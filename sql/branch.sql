BEGIN;
    -- In some cases, we don't have a participant linked to emails
    ALTER TABLE email_queue ALTER COLUMN participant DROP NOT NULL;

    -- Email address to send emails to. If not provided, participant's primary email will be used.
    ALTER TABLE email_queue ADD COLUMN email_address text;

    ALTER TABLE email_queue ADD CONSTRAINT email_or_participant_required
          CHECK ((participant IS NOT NULL) OR (email_address IS NOT NULL));
END;
