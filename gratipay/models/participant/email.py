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

( VERIFICATION_MISSING
, VERIFICATION_FAILED
, VERIFICATION_EXPIRED
, VERIFICATION_REDUNDANT
, VERIFICATION_STYMIED
, VERIFICATION_SUCCEEDED
 ) = range(6)


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
        :param Package packages: packages to optionally also verify ownership of

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

        extra_sql, values = '', []
        for p in packages:
            extra_sql += ' (%s, %s)'
            values += [nonce, p.id]
        c.run('INSERT INTO claims (nonce, package_id) VALUES' + extra_sql, values)
        self.app.add_event( c
                          , 'participant'
                          , dict( id=self.id
                                , action='start-claim'
                                , values=dict(package_ids=[p.id for p in packages])
                                 )
                               )


    def update_email(self, email):
        """Set the email address for the participant.
        """
        if not getattr(self.get_email(email), 'verified', False):
            raise EmailNotVerified()
        username = self.username
        with self.db.get_cursor() as c:
            self.app.add_event( c
                              , 'participant'
                              , dict(id=self.id, action='set', values=dict(primary_email=email))
                               )
            c.run("""
                UPDATE participants
                   SET email_address=%(email)s
                 WHERE username=%(username)s
            """, locals())
        self.set_attributes(email_address=email)


    def verify_email(self, email, nonce):
        if '' in (email, nonce):
            return VERIFICATION_MISSING
        r = self.get_email(email)
        if r is None:
            return VERIFICATION_FAILED
        if r.verified:
            assert r.nonce is None  # and therefore, order of conditions matters
            return VERIFICATION_REDUNDANT
        if not constant_time_compare(r.nonce, nonce):
            return VERIFICATION_FAILED
        if (utcnow() - r.verification_start) > EMAIL_HASH_TIMEOUT:
            return VERIFICATION_EXPIRED
        try:
            self.db.run("""
                UPDATE emails
                   SET verified=true, verification_end=now(), nonce=NULL
                 WHERE participant_id=%s
                   AND address=%s
                   AND verified IS NULL
            """, (self.id, email))
        except IntegrityError:
            return VERIFICATION_STYMIED

        if not self.email_address:
            self.update_email(email)
        return VERIFICATION_SUCCEEDED


    def get_email(self, email):
        """Return a record for a single email address on file for this participant.
        """
        return self.db.one("""
            SELECT *
              FROM emails
             WHERE participant_id=%s
               AND address=%s
        """, (self.id, email))


    def get_emails(self):
        """Return a list of all email addresses on file for this participant.
        """
        return self.db.all("""
            SELECT *
              FROM emails
             WHERE participant_id=%s
          ORDER BY id
        """, (self.id,))


    def get_verified_email_addresses(self):
        """Return a list of verified email addresses on file for this participant.
        """
        return [email.address for email in self.get_emails() if email.verified]


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
