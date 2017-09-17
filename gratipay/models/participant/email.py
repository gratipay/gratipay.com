# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import uuid
from datetime import timedelta

from aspen.utils import utcnow
from psycopg2 import IntegrityError

import gratipay
from gratipay.exceptions import EmailAlreadyVerified, EmailTaken, CannotRemovePrimaryEmail
from gratipay.exceptions import EmailNotVerified, TooManyEmailAddresses, EmailNotOnFile
from gratipay.security.crypto import constant_time_compare
from gratipay.utils import encode_for_querystring


EMAIL_HASH_TIMEOUT = timedelta(hours=24)


class VerificationResult(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "<VerificationResult: %r>" % self.name
    __str__ = __repr__


#: Signal that verifying an email address failed.
VERIFICATION_FAILED = VerificationResult('Failed')

#: Signal that verifying an email address was redundant.
VERIFICATION_REDUNDANT = VerificationResult('Redundant')

#: Signal that an email address is already verified for a different :py:class:`Participant`.
VERIFICATION_STYMIED = VerificationResult('Stymied')

#: Signal that email verification succeeded.
VERIFICATION_SUCCEEDED = VerificationResult('Succeeded')


class Email(object):
    """Participants may associate email addresses with their account.

    Email addresses are stored in an ``email_addresses`` table in the database,
    which holds the addresses themselves as well as info related to address
    verification. While a participant may have multiple email addresses on
    file, verified or not, only one will be the *primary* email address: the
    one also recorded in ``participants.email_address``. It's a bug for the
    primary address not to be verified, or for an address to be in
    ``participants.email_address`` but not also in ``email_addresses``.

    Having a verified email is a prerequisite for certain other features on
    Gratipay, such as linking a PayPal account, or filing a national identity.

    """

    @property
    def has_pending_email_address_verifications(self):
        """A boolean indicating whether there are email address verifications
        outstanding for this participant. Makes a db call.
        """
        for email in self.get_emails():
            if not email.verified:
                return True
        return False


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
              FROM email_addresses
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
        existing = c.one( 'SELECT * FROM email_addresses WHERE address=%s AND participant_id=%s'
                        , (email, self.id)
                         )  # can't use eafp here because of cursor error handling
                            # XXX I forget what eafp is. :(

        if existing is None:

            # Not in the table yet. This should throw an IntegrityError if the
            # address is verified for a different participant.

            c.run( "INSERT INTO email_addresses (participant_id, address, nonce) "
                   "VALUES (%s, %s, %s)"
                 , (self.id, email, nonce)
                  )
        else:

            # Already in the table. Restart verification. Henceforth, old links
            # will fail.

            if existing.nonce:
                c.run('DELETE FROM claims WHERE nonce=%s', (existing.nonce,))
            c.run("""
                UPDATE email_addresses
                   SET nonce=%s
                     , verification_start=now()
                 WHERE participant_id=%s
                   AND address=%s
            """, (nonce, self.id, email))

        return nonce


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
        _fail = VERIFICATION_FAILED, None, None
        if '' in (email.strip(), nonce.strip()):
            return _fail
        with self.db.get_cursor() as cursor:

            # Load an email record. Check for an address match, but don't check
            # the nonce at this point. We want to compare in constant time to
            # avoid timing attacks, and we'll do that below.

            record = self.get_email(email, cursor, and_lock=True)
            if record is None:

                # We don't have that email address on file. Maybe it used to be
                # on file but was explicitly removed (they followed an old link
                # after removing in the UI?), or maybe it was never on file in
                # the first place (they munged the querystring?).

                return _fail

            if record.nonce is None:

                # Nonces are nulled out only when updating to mark an email
                # address as verified; we always set a nonce when inserting.
                # Therefore, the main way to get a null nonce is to issue a
                # link, follow it, and follow it again.

                # All records with a null nonce should be verified, though not
                # all verified records will have a null nonce. That is, it's
                # possible to land here with an already-verified address, and
                # this is in fact expected when verifying package ownership via
                # an already-verified address.

                assert record.verified

                return VERIFICATION_REDUNDANT, None, None


            # *Now* verify that the nonce given matches the one expected, along
            # with the time window for verification.

            if not constant_time_compare(record.nonce, nonce):
                return _fail
            if (utcnow() - record.verification_start) > EMAIL_HASH_TIMEOUT:
                return _fail


            # And now we can load any packages associated with the nonce, and
            # save the address.

            packages = self.get_packages_claiming(cursor, nonce)
            paypal_updated = None
            try:
                if packages:
                    paypal_updated = False
                    self.finish_package_claims(cursor, nonce, *packages)
                self.save_email_address(cursor, email)
                has_no_paypal = not self.get_payout_routes(good_only=True)
                if packages and has_no_paypal:
                    self.set_paypal_address(email, cursor)
                    paypal_updated = True
            except IntegrityError:
                return VERIFICATION_STYMIED, None, None
            return VERIFICATION_SUCCEEDED, packages, paypal_updated


    def save_email_address(self, cursor, address):
        """Given an email address, modify the database.

        This is where we actually mark the email address as verified.
        Additionally, we clear out any competing claims to the same address.

        """
        cursor.run("""
            UPDATE email_addresses
               SET verified=true, verification_end=now(), nonce=NULL
             WHERE participant_id=%s
               AND address=%s
               AND verified IS NULL
        """, (self.id, address))
        cursor.run("""
            DELETE
              FROM email_addresses
             WHERE participant_id != %s
               AND address=%s
        """, (self.id, address))
        if not self.email_address:
            self.set_primary_email(address, cursor)


    def get_email(self, address, cursor=None, and_lock=False):
        """Return a record for a single email address on file for this participant.

        :param unicode address: the email address for which to get a record
        :param Cursor cursor: a database cursor; if ``None``, we'll use ``self.db``
        :param and_lock: if True, we will acquire a write-lock on the email record before returning
        :returns: a database record (a named tuple)

        """
        sql = 'SELECT * FROM email_addresses WHERE participant_id=%s AND address=%s'
        if and_lock:
            sql += ' FOR UPDATE'
        return (cursor or self.db).one(sql, (self.id, address))


    def get_emails(self, cursor=None):
        """Return a list of all email addresses on file for this participant.
        """
        return (cursor or self.db).all("""
            SELECT *
              FROM email_addresses
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
            c.run("DELETE FROM email_addresses WHERE participant_id=%s AND address=%s",
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
