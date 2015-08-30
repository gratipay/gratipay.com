BEGIN;

    ALTER TABLE participants DROP COLUMN anonymous_receiving;
    ALTER TABLE participants DROP COLUMN npatrons;
    ALTER TABLE participants DROP COLUMN receiving;

    ALTER TABLE participants ADD COLUMN ngiving_to INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE participants ADD COLUMN ntaking_from INTEGER NOT NULL DEFAULT 0;

    ALTER TABLE teams RENAME COLUMN nsupporters TO nreceiving_from;
    ALTER TABLE teams RENAME COLUMN nmembers TO ndistributing_to;
    ALTER TABLE teams RENAME COLUMN payroll TO distributing;
END;
