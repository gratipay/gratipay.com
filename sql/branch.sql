ALTER TABLE emails DROP CONSTRAINT emails_participant_fkey;

ALTER TABLE emails ALTER COLUMN participant TYPE bigint USING participant::bigint;

CREATE SEQUENCE emails_participant_seq;
ALTER TABLE emails ALTER COLUMN participant SET DEFAULT nextval('emails_participant_seq');
ALTER SEQUENCE emails_participant_seq OWNED BY emails.participant;

ALTER TABLE emails ADD FOREIGN KEY (participant) REFERENCES participants(id) ON UPDATE CASCADE ON DELETE RESTRICT;
