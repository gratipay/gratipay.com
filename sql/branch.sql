BEGIN;
    ALTER TABLE packages ALTER COLUMN readme_raw DROP NOT NULL;
    ALTER TABLE packages ALTER COLUMN readme_raw SET DEFAULT NULL;
    UPDATE packages SET readme_raw=NULL;
END;
