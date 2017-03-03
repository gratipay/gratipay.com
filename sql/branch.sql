BEGIN;

    ALTER TABLE email_queue ADD COLUMN user_initiated bool NOT NULL DEFAULT TRUE;

END;
