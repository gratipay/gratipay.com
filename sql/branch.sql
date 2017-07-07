BEGIN;
    -- In some cases, we don't have a participant linked to emails
    ALTER TABLE email_queue ALTER COLUMN participant DROP NOT NULL;

    -- Email address to send emails to. If not provided, participant's primary email will be used.
    ALTER TABLE email_queue ADD COLUMN email_address text;

    ALTER TABLE email_queue ADD CONSTRAINT email_or_participant_required
          CHECK ((participant IS NOT NULL) OR (email_address IS NOT NULL));
END;

BEGIN;
    CREATE TABLE email_auth_nonces
    ( id                    serial                      PRIMARY KEY
    , email_address         text                        NOT NULL
    , nonce                 text                        NOT NULL
    , ctime                 timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , UNIQUE (nonce)
     );
END;
