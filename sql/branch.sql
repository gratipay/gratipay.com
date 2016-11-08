BEGIN;
    ALTER TABLE packages ALTER COLUMN readme DROP NOT NULL;
    ALTER TABLE packages ALTER COLUMN readme SET DEFAULT NULL;
    UPDATE packages SET readme=NULL;
    ALTER TABLE packages ADD COLUMN readme_needs_to_be_processed bool NOT NULL DEFAULT true;
END;
