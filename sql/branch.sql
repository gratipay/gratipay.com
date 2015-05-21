BEGIN;

    ALTER TABLE teams ADD COLUMN revenue_model text NOT NULL DEFAULT '';

END;
