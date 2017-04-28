BEGIN;
    ALTER TABLE participants DROP COLUMN email;
    DROP TYPE email_address_with_confirmation;
END;
