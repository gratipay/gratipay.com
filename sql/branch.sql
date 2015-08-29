BEGIN;

    ALTER TABLE participants DROP COLUMN anonymous_receiving;
    ALTER TABLE participants DROP COLUMN npatrons;
    ALTER TABLE participants DROP COLUMN receiving;

END;
