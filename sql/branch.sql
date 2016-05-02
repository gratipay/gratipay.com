CREATE TABLE countries -- http://www.iso.org/iso/country_codes
( id    bigserial   primary key
, code2 text        NOT NULL UNIQUE
, code3 text        NOT NULL UNIQUE
, name  text        NOT NULL UNIQUE
 );

\i sql/countries.sql

CREATE TABLE participant_identities
( id                bigserial   primary key
, participant_id    bigint      NOT NULL REFERENCES participants(id)
, country_id        bigint      NOT NULL REFERENCES countries(id)
, schema_name       text        NOT NULL
, info              bytea       NOT NULL
, is_verified       boolean     NOT NULL DEFAULT false
, UNIQUE(participant_id, country_id)
 );


-- participants.has_verified_identity

ALTER TABLE participants ADD COLUMN has_verified_identity bool NOT NULL DEFAULT false;

CREATE FUNCTION update_has_verified_identity() RETURNS trigger AS $$
    BEGIN
        UPDATE participants p
           SET has_verified_identity=COALESCE((
                SELECT is_verified
                  FROM participant_identities
                 WHERE participant_id = OLD.participant_id
                   AND is_verified
                 LIMIT 1
               ), false)
         WHERE p.id = OLD.participant_id;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER propagate_is_verified_changes
    AFTER UPDATE OF is_verified ON participant_identities
    FOR EACH ROW
    EXECUTE PROCEDURE update_has_verified_identity();

CREATE TRIGGER propagate_is_verified_removal
    AFTER DELETE ON participant_identities
    FOR EACH ROW
    EXECUTE PROCEDURE update_has_verified_identity();

-- We don't need an INSERT trigger, because of the way the defaults play out.
