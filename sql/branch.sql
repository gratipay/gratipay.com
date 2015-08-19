BEGIN;

    ALTER TABLE teams DROP COLUMN revenue_model;
    ALTER TABLE teams DROP COLUMN getting_involved;
    ALTER TABLE teams DROP COLUMN getting_paid;

END;
