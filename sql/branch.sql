CREATE TABLE participant_identities
( id                bigserial   primary key
, participant_id    bigint      NOT NULL REFERENCES participants(id)
, country_id        bigint      NOT NULL REFERENCES countries(id)
, schema_name       text        NOT NULL
, info              bytea       NOT NULL
, UNIQUE(participant_id, country_id)
 );
