# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid
from datetime import timedelta

from aspen.utils import utcnow
from psycopg2 import IntegrityError

import gratipay
from gratipay.exceptions import EmailAlreadyVerified, EmailTaken, CannotRemovePrimaryEmail
from gratipay.exceptions import EmailNotVerified, TooManyEmailAddresses, EmailNotOnFile, NoPackages
from gratipay.security.crypto import constant_time_compare
from gratipay.utils import encode_for_querystring


EMAIL_HASH_TIMEOUT = timedelta(hours=24)


#: Signal that verifying an email address failed.
VERIFICATION_FAILED = object()

#: Signal that verifying an email address was redundant.
VERIFICATION_REDUNDANT = object()

#: Signal that an email address is already verified for a different :py:class:`Participant`.
VERIFICATION_STYMIED = object()

#: Signal that email verification succeeded.
VERIFICATION_SUCCEEDED = object()


class Email(object):
    """Participants may associate email addresses with their account.

    Email addresses are stored in an ``emails`` table in the database, which
    holds the addresses themselves as well as info related to address
    verification. While a participant may have multiple email addresses on
    file, verified or not, only one will be the *primary* email address: the
    one also recorded in ``participants.email_address``. It's a bug for the
    primary address not to be verified, or for an address to be in
    ``participants.email_address`` but not also in ``emails``.

    Having a verified email is a prerequisite for certain other features on
    Gratipay, such as linking a PayPal account, or filing a national identity.

    """

    def start_email_verification(self, email, *packages):
        """Add an email address for a participant.

        This is called when adding a new email address, and when resending the
        verification email for an unverified email address.

        :param unicode email: the email address to add
        :param gratipay.models.package.Package packages: packages to optionally
            also verify ownership of

        :returns: ``None``

        :raises EmailAlreadyVerified: if the email is already verified for
            this participant (unless they're claiming packages)
        :raises EmailTaken: if the email is verified for a different participant
        :raises EmailNotOnFile: if the email address is not on file for any of
            the packages
        :raises TooManyEmailAddresses: if the participant already has 10 emails
        :raises Throttled: if the participant adds too many emails too quickly

        """
        with self.db.get_cursor() as c:
            self.validate_email_verification_request(c, email, *packages)
            link = self.get_email_verification_link(c, email, *packages)

        verified_emails = self.get_verified_email_addresses()
        kwargs = dict( npackages=len(packages)
                     , package_name=packages[0].name if packages else ''
                     , new_email=email
                     , new_email_verified=email in verified_emails
                     , link=link
                     , include_unsubscribe=False
                      )
        self.app.email_queue.put(self, 'verification', email=email, **kwargs)
        if self.email_address and self.email_address != email:
            self.app.email_queue.put( self
                                    , 'verification-notice'

                                    # Don't count this one against their sending quota.
                                    # It's going to their own verified address, anyway.
                                    , _user_initiated=False

                                    , **kwargs
                                     )


    def validate_email_verification_request(self, c, email, *packages):
        """Given a cursor, email, and packages, return ``None`` or raise.
        """
        if not all(email in p.emails for p in packages):
            raise EmailNotOnFile()

        owner_id = c.one("""
            SELECT participant_id
              FROM emails
             WHERE address = %(email)s
               AND verified IS true
        """, dict(email=email))

        if owner_id:
            if owner_id != self.id:
                raise EmailTaken()
            elif packages:
                pass  # allow reverify if claiming packages
            else:
                raise EmailAlreadyVerified()

        if len(self.get_emails()) > 9:
            if owner_id and owner_id == self.id and packages:
                pass  # they're using an already-verified email to verify packages
            else:
                raise TooManyEmailAddresses()


    def get_email_verification_link(self, c, email, *packages):
        """Get a link to complete an email verification workflow.

        :param Cursor c: the cursor to use
        :param unicode email: the email address to be verified

        :param packages: :py:class:`~gratipay.models.package.Package` objects
            for which a successful verification will also entail verification of
            ownership of the package

        :returns: a URL by which to complete the verification process

        """
        self.app.add_event( c
                          , 'participant'
                          , dict(id=self.id, action='add', values=dict(email=email))
                           )
        nonce = self.get_email_verification_nonce(c, email)
        if packages:
            self.start_package_claims(c, nonce, *packages)
        link = "{base_url}/~{username}/emails/verify.html?email2={encoded_email}&nonce={nonce}"
        return link.format( base_url=gratipay.base_url
                          , username=self.username_lower
                          , encoded_email=encode_for_querystring(email)
                          , nonce=nonce
                           )


    def get_email_verification_nonce(self, c, email):
        """Given a cursor and email address, return a verification nonce.
        """
        nonce = str(uuid.uuid4())
        existing = c.one( 'SELECT * FROM emails WHERE address=%s AND participant_id=%s'
                        , (email, self.id)
                         )  # can't use eafp here because of cursor error handling

        if existing is None:

            # Not in the table yet. This should throw an IntegrityError if the
            # address is verified for a different participant.

            c.run( "INSERT INTO emails (participant_id, address, nonce) VALUES (%s, %s, %s)"
                 , (self.id, email, nonce)
                  )
        else:

            # Already in the table. Restart verification. Henceforth, old links
            # will fail.

            if existing.nonce:
                c.run('DELETE FROM claims WHERE nonce=%s', (existing.nonce,))
            c.run("""
                UPDATE emails
                   SET nonce=%s
                     , verification_start=now()
                 WHERE participant_id=%s
                   AND address=%s
            """, (nonce, self.id, email))

        return nonce


    def start_package_claims(self, c, nonce, *packages):
        """Takes a cursor, nonce and list of packages, inserts into ``claims``
        and returns ``None`` (or raise :py:exc:`NoPackages`).
        """
        if not packages:
            raise NoPackages()

        # We want to make a single db call to insert all claims, so we need to
        # do a little SQL construction. Do it in such a way that we still avoid
        # Python string interpolation (~= SQLi vector).

        extra_sql, values = [], []
        for p in packages:
            extra_sql.append('(%s, %s)')
            values += [nonce, p.id]
        c.run('INSERT INTO claims (nonce, package_id) VALUES' + ', '.join(extra_sql), values)
        self.app.add_event( c
                          , 'participant'
                          , dict( id=self.id
                                , action='start-claim'
                                , values=dict(package_ids=[p.id for p in packages])
                                 )
                               )


    def set_primary_email(self, email, cursor=None):
        """Set the primary email address for the participant.
        """
        if cursor:
            self._set_primary_email(email, cursor)
        else:
            with self.db.get_cursor() as cursor:
                self._set_primary_email(email, cursor)
        self.set_attributes(email_address=email)


    def _set_primary_email(self, email, cursor):
        if not getattr(self.get_email(email, cursor), 'verified', False):
            raise EmailNotVerified()
        self.app.add_event( cursor
                          , 'participant'
                          , dict(id=self.id, action='set', values=dict(primary_email=email))
                           )
        cursor.run("""
            UPDATE participants
               SET email_address=%(email)s
             WHERE username=%(username)s
        """, dict(email=email, username=self.username))


    def finish_email_verification(self, email, nonce):
        """Given an email address and a nonce as strings, return a three-tuple:

        - a ``VERIFICATION_*`` constant;
        - a list of packages if ``VERIFICATION_SUCCEEDED`` (``None``
          otherwise), and
        - a boolean indicating whether the participant's PayPal address was
          updated if applicable (``None`` if not).

        """
        if '' in (email.strip(), nonce.strip()):
            return VERIFICATION_FAILED, None, None
        with self.db.get_cursor() as cursor:
            record = self.get_email(email, cursor, and_lock=True)
            if record is None:
                return VERIFICATION_FAILED, None, None
            packages = self.get_packages_claiming(cursor, nonce)
            if record.verified and not packages:
                assert record.nonce is None  # and therefore, order of conditions matters
                return VERIFICATION_REDUNDANT, None, None
            if not constant_time_compare(record.nonce, nonce):
                return VERIFICATION_FAILED, None, None
            if (utcnow() - record.verification_start) > EMAIL_HASH_TIMEOUT:
                return VERIFICATION_FAILED, None, None
            try:
                paypal_updated = False
                if packages:
                    self.finish_package_claims(cursor, nonce, *packages)
                self.save_email_address(cursor, email)
                has_no_paypal = not self.get_payout_routes(good_only=True)
                if packages and has_no_paypal:
                    self.set_paypal_address(email, cursor)
                    paypal_updated = True
            except IntegrityError:
                return VERIFICATION_STYMIED, None, None
            return VERIFICATION_SUCCEEDED, packages, paypal_updated


    def get_packages_claiming(self, cursor, nonce):
        """Given a nonce, return :py:class:`~gratipay.models.package.Package`
        objects associated with it.
        """
        return cursor.all("""
            SELECT p.*::packages
              FROM packages p
              JOIN claims c
                ON p.id = c.package_id
             WHERE c.nonce=%s
          ORDER BY p.name ASC
        """, (nonce,))


    def save_email_address(self, cursor, address):
        """Given an email address, modify the database.

        This is where we actually mark the email address as verified.
        Additionally, we clear out any competing claims to the same address.

        """
        cursor.run("""
            UPDATE emails
               SET verified=true, verification_end=now(), nonce=NULL
             WHERE participant_id=%s
               AND address=%s
               AND verified IS NULL
        """, (self.id, address))
        cursor.run("""
            DELETE
              FROM emails
             WHERE participant_id != %s
               AND address=%s
        """, (self.id, address))
        if not self.email_address:
            self.set_primary_email(address, cursor)


    def finish_package_claims(self, cursor, nonce, *packages):
        """Create teams if needed and associate them with the packages.
        """
        if not packages:
            raise NoPackages()

        package_ids, teams, team_ids = [], [], []
        for package in packages:
            package_ids.append(package.id)
            team = package.get_or_create_linked_team(cursor, self)
            teams.append(team)
            team_ids.append(team.id)
        review_url = self.app.project_review_repo.create_issue(*teams)

        cursor.run('DELETE FROM claims WHERE nonce=%s', (nonce,))
        cursor.run('UPDATE teams SET review_url=%s WHERE id=ANY(%s)', (review_url, team_ids,))
        self.app.add_event( cursor
                          , 'participant'
                          , dict( id=self.id
                                , action='finish-claim'
                                , values=dict(package_ids=package_ids)
                                 )
                               )


    def get_email(self, address, cursor=None, and_lock=False):
        """Return a record for a single email address on file for this participant.

        :param unicode address: the email address for which to get a record
        :param Cursor cursor: a database cursor; if ``None``, we'll use ``self.db``
        :param and_lock: if True, we will acquire a write-lock on the email record before returning
        :returns: a database record (a named tuple)

        """
        sql = 'SELECT * FROM emails WHERE participant_id=%s AND address=%s'
        if and_lock:
            sql += ' FOR UPDATE'
        return (cursor or self.db).one(sql, (self.id, address))


    def get_emails(self, cursor=None):
        """Return a list of all email addresses on file for this participant.
        """
        return (cursor or self.db).all("""
            SELECT *
              FROM emails
             WHERE participant_id=%s
          ORDER BY id
        """, (self.id,))


    def get_verified_email_addresses(self, cursor=None):
        """Return a list of verified email addresses on file for this participant.
        """
        return [email.address for email in self.get_emails(cursor) if email.verified]


    def remove_email(self, address):
        """Remove the given email address from the participant's account.
        Raises ``CannotRemovePrimaryEmail`` if the address is primary. It's a
        noop if the email address is not on file.
        """
        if address == self.email_address:
            raise CannotRemovePrimaryEmail()
        with self.db.get_cursor() as c:
            self.app.add_event( c
                              , 'participant'
                              , dict(id=self.id, action='remove', values=dict(email=address))
                               )
            c.run("DELETE FROM emails WHERE participant_id=%s AND address=%s",
                  (self.id, address))


    def set_email_lang(self, accept_lang):
        """Given a language identifier, set it for the participant as their
        preferred language in which to receive email.
        """
        if not accept_lang:
            return
        self.db.run("UPDATE participants SET email_lang=%s WHERE id=%s",
                    (accept_lang, self.id))
        self.set_attributes(email_lang=accept_lang)
