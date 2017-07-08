import datetime
import uuid

from aspen.utils import utcnow


class VerificationResult(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<VerificationResult: %r>" % self.name
    __str__ = __repr__

#: Signal that the nonce doesn't exist in our database
NONCE_INVALID = VerificationResult('Invalid')

#: Signal that the nonce exists, but has expired
NONCE_EXPIRED = VerificationResult('Expired')

#: Signal that the nonce exists, and is valid
NONCE_VALID = VerificationResult('Valid')

#: Time for nonce to expire
NONCE_EXPIRY_MINUTES = 60


def create_nonce(db, email_address):
    nonce = str(uuid.uuid4())
    db.run("""
        INSERT INTO email_auth_nonces (email_address, nonce)
             VALUES (%(email_address)s, %(nonce)s)
    """, locals())

    return nonce


def verify_nonce(db, email_address, nonce):
    record = db.one("""
        SELECT email_address, ctime
          FROM email_auth_nonces
         WHERE nonce = %(nonce)s
           AND email_address = %(email_address)s
    """, locals(), back_as=dict)

    if not record:
        return NONCE_INVALID

    if utcnow() - record['ctime'] > datetime.timedelta(minutes=NONCE_EXPIRY_MINUTES):
        return NONCE_EXPIRED

    return NONCE_VALID


def invalidate_nonce(db, email_address, nonce):
    db.run("""
        DELETE FROM email_auth_nonces
         WHERE nonce = %(nonce)s
           AND email_address = %(email_address)s
    """, locals())
