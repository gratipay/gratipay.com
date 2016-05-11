CREATE TABLE countries -- http://www.iso.org/iso/country_codes
( id    bigserial   primary key
, code2 text        NOT NULL UNIQUE
, code3 text        NOT NULL UNIQUE
, name  text        NOT NULL UNIQUE
 );

\i sql/countries.sql

CREATE TABLE participant_identities
( id                bigserial       primary key
, participant_id    bigint          NOT NULL REFERENCES participants(id)
, country_id        bigint          NOT NULL REFERENCES countries(id)
, schema_name       text            NOT NULL
, info              bytea           NOT NULL
, _info_last_keyed  timestamptz     NOT NULL DEFAULT now()
, is_verified       boolean         NOT NULL DEFAULT false
, UNIQUE(participant_id, country_id)
 );


-- fail_if_no_email

CREATE FUNCTION fail_if_no_email() RETURNS trigger AS $$
    BEGIN
        IF (SELECT email_address FROM participants WHERE id=NEW.participant_id) IS NULL THEN
            RAISE EXCEPTION
            USING ERRCODE=23100
                , MESSAGE='This operation requires a verified participant email address.';
        END IF;
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_email_for_participant_identity
    BEFORE INSERT ON participant_identities
    FOR EACH ROW
    EXECUTE PROCEDURE fail_if_no_email();


-- participants.has_verified_identity

ALTER TABLE participants ADD COLUMN has_verified_identity bool NOT NULL DEFAULT false;


-- https://github.com/gratipay/gratipay.com/pull/4018

BEGIN;

    -- Farewell, old takes table!
    DROP VIEW current_takes;
    DROP TABLE takes;

    -- Be gone, payroll! I never knew you.
    DROP VIEW current_payroll;
    DROP TABLE payroll;

    -- takes - how participants express membership in teams
    CREATE TABLE takes
    ( id                bigserial                   PRIMARY KEY
    , ctime             timestamp with time zone    NOT NULL
    , mtime             timestamp with time zone    NOT NULL DEFAULT now()
    , participant_id    bigint                      NOT NULL REFERENCES participants(id)
    , team_id           bigint                      NOT NULL REFERENCES teams(id)
    , ntakes            int                         NOT NULL
    , recorder_id       bigint                      NOT NULL REFERENCES participants(id)
    , CONSTRAINT not_negative CHECK (ntakes >= 0)
     );

    CREATE VIEW memberships AS
        SELECT * FROM (
             SELECT DISTINCT ON (participant_id, team_id) t.*
               FROM takes t
               JOIN participants p ON p.id = t.participant_id
              WHERE p.is_suspicious IS NOT TRUE
           ORDER BY participant_id
                  , team_id
                  , mtime DESC
        ) AS anon WHERE ntakes > 0;

    ALTER TABLE teams ADD COLUMN ntakes int default 0;
    ALTER TABLE teams ADD COLUMN ntakes_unclaimed int default 0;
    ALTER TABLE teams ADD COLUMN ntakes_claimed int default 0;
    ALTER TABLE teams ADD CONSTRAINT ntakes_sign CHECK (ntakes >= 0);
    ALTER TABLE teams ADD CONSTRAINT ntakes_sum CHECK (ntakes = ntakes_claimed + ntakes_unclaimed);

END;
