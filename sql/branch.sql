BEGIN;

    ALTER TABLE payments ADD CONSTRAINT positive CHECK (amount > 0);

END;
