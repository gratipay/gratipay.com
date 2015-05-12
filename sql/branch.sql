BEGIN;

    ALTER TABLE participants DROP COLUMN pledging;
    ALTER TABLE participants DROP COLUMN notify_on_opt_in;

END;
