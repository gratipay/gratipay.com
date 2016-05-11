from __future__ import absolute_import, division, print_function, unicode_literals

from psycopg2 import IntegrityError
from gratipay.models import add_event


class ParticipantIdentityError(StandardError): pass
class ParticipantIdentitySchemaUnknown(ParticipantIdentityError): pass
class ParticipantIdentityInfoInvalid(ParticipantIdentityError): pass


schema_validators = {'nothing-enforced': lambda info: None}


def _validate_info(schema_name, info):
    if schema_name not in schema_validators:
        raise ParticipantIdentitySchemaUnknown("unknown schema '{}'".format(schema_name))
    validate_schema = schema_validators[schema_name]
    validate_schema(info)
    return None


class IdentityMixin(object):
    """This mixin provides management of national identities for
    :py:class:`~gratipay.models.participant.Participant` objects.

    A participant may have zero or more national identities on file with
    Gratipay, with at most one for any given country at any given time. When at
    least one of a participant's national identities has been verified, then
    they may join the payroll of one or more Teams.

    Since national identity information is more sensitive than other
    information in our database, we encrypt it in the application layer before
    passing it to the database in :py:meth:`store_identity_info`. We then limit
    access to the information to a single method,
    :py:meth:`retrieve_identity_info`.

    """

    def store_identity_info(self, country_id, schema_name, info):
        """Store the participant's national identity information for a given country.

        :param int country_id: an ``id`` from the ``countries`` table
        :param dict schema_name: the name of the schema of the identity information
        :param dict info: a dictionary of identity information

        :returns: the ``id`` of the identity info's record in the
            ``participant_identities`` table

        :raises ParticipantIdentitySchemaUnknown: if ``schema_name`` doesn't
            name a known schema
        :raises ParticipantIdentityInfoInvalid: if the ``info`` dictionary does
            not conform to the schema named by ``schema_name``

        The ``info`` dictionary will be serialized to JSON and then encrypted
        with :py:class:`~gratipay.security.crypto.EncryptingPacker` before
        being sent to the database. We anticipate multiple schemas evolving for
        this dictionary, with enforcement in the application layer (since the
        field is opaque in the database layer). For now there is only one
        available schema: ``nothing-enforced``.

        """
        _validate_info(schema_name, info)
        info = self.encrypting_packer.pack(info)

        def _add_event(action):
            payload = dict( id=self.id
                          , country_id=country_id
                          , identity_id=identity_id
                          , action=action + ' identity'
                           )
            add_event(cursor, 'participant', payload)

        params = dict( participant_id=self.id
                     , country_id=country_id
                     , info=info
                     , schema_name=schema_name
                      )

        try:
            with self.db.get_cursor() as cursor:
                identity_id = cursor.one("""

                    INSERT INTO participant_identities
                                (participant_id, country_id, schema_name, info)
                         VALUES (%(participant_id)s, %(country_id)s, %(schema_name)s, %(info)s)
                      RETURNING id

                """, params)
                _add_event('insert')

        except IntegrityError as exc:
            if exc.pgcode != '23505':
                raise
            with self.db.get_cursor() as cursor:
                identity_id, old_schema_name = cursor.one("""

                    UPDATE participant_identities
                       SET schema_name=%(schema_name)s, info=%(info)s
                     WHERE participant_id=%(participant_id)s
                       AND country_id=%(country_id)s
                 RETURNING id, schema_name

                """, params)
                _add_event('update')

        return identity_id


    def retrieve_identity_info(self, country_id):
        """Return the participant's national identity information for a given country.

        :param int country_id: an ``id`` from the ``countries`` table

        :returns: a dictionary of identity information, or ``None``

        """
        with self.db.get_cursor() as cursor:
            identity_id, info = cursor.one("""

                SELECT id, info
                  FROM participant_identities
                 WHERE participant_id=%s
                   AND country_id=%s

            """, (self.id, country_id), default=(None, None))

            if info is not None:
                info = bytes(info) # psycopg2 returns bytea as buffer; we want bytes
                info = self.encrypting_packer.unpack(info)

            payload = dict( id=self.id
                          , identity_id=identity_id
                          , country_id=country_id
                          , action='retrieve identity'
                           )

            add_event(cursor, 'participant', payload)

        return info


    def list_identity_metadata(self):
        """Return a list of identity metadata records, sorted by country name.

        Identity metadata records have the following attributes:

        :var int id: the record's primary key in the ``participant_identities`` table
        :var Country country: the country this identity applies to
        :var unicode schema_name: the name of the schema that the data itself conforms to

        The national identity information itself is not included, only
        metadata. Use :py:meth:`retrieve_identity_info` to get the actual data.

        """
        return self.db.all("""

            SELECT pi.id
                 , c.*::countries AS country
                 , schema_name
              FROM participant_identities pi
              JOIN countries c ON pi.country_id=c.id
             WHERE participant_id=%s
          ORDER BY c.code

        """, (self.id,))


# Rekeying
# ========

def rekey(db, packer):
    """Rekey the encrypted participant identity information in our database.

    :param GratipayDB db: used to access the database
    :param EncryptingPacker packer: used to decrypt and encrypt data

    This function features prominently in our procedure for rekeying our
    encrypted data, as documented in the "`Keep Secrets`_" howto. It operates
    by loading records from `participant_identities` that haven't been updated
    in the present month, in batches of 100. It updates a timestamp atomically
    with each rekeyed `info`, so it can be safely rerun in the face of network
    failure, etc.

    .. _Keep Secrets: http://inside.gratipay.com/howto/keep-secrets

    """
    n = 0
    while 1:
        m = _rekey_one_batch(db, packer)
        if m == 0:
            break
        n += m
    return n


def _rekey_one_batch(db, packer):
    batch = db.all("""

        SELECT id, info
          FROM participant_identities
         WHERE _info_last_keyed < date_trunc('month', now())
      ORDER BY _info_last_keyed ASC
         LIMIT 100

    """)
    if not batch:
        return 0

    for rec in batch:
        plaintext = packer.unpack(bytes(rec.info))
        new_token = packer.pack(plaintext)
        db.run( "UPDATE participant_identities SET info=%s, _info_last_keyed=now() WHERE id=%s"
              , (new_token, rec.id)
               )

    return len(batch)
