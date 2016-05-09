CREATE TABLE participant_identities
( id                bigserial   primary key
, participant_id    bigint      NOT NULL REFERENCES participants(id)
, country_id        bigint      NOT NULL REFERENCES countries(id)
, schema_name       text        NOT NULL
, info              bytea       NOT NULL
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
