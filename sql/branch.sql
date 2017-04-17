BEGIN;
    ALTER TABLE participants ADD COLUMN balance_1_0 numeric(35,2) NOT NULL DEFAULT 0;
END;
