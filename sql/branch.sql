BEGIN;

    ALTER TABLE payments ADD CONSTRAINT positive CHECK (amount > 0) NOT VALID;

END;
