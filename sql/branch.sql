BEGIN;

    ALTER TABLE participants DROP COLUMN anonymous_receiving;
    ALTER TABLE participants DROP COLUMN npatrons;
    ALTER TABLE participants DROP COLUMN receiving;

    ALTER TABLE participants ADD COLUMN ngiving_to INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE participants ADD COLUMN ntaking_from INTEGER NOT NULL DEFAULT 0;
END;
