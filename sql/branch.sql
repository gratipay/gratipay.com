BEGIN;
    ALTER TABLE emails RENAME TO email_addresses;
    ALTER TABLE email_queue RENAME TO email_messages;
    ALTER TABLE email_messages ADD COLUMN result text;
    ALTER TABLE email_messages ADD COLUMN remote_message_id text;

    -- transfer dead to result
    UPDATE email_messages SET result='unknown failure' WHERE dead;
    ALTER TABLE email_messages DROP COLUMN dead;

    -- assume success for the rest
    UPDATE email_messages SET result='' WHERE result is null;
END;
