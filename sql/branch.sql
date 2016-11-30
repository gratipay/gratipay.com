BEGIN;
    ALTER TABLE packages DROP COLUMN readme;
    ALTER TABLE packages DROP COLUMN readme_raw;
    ALTER TABLE packages DROP COLUMN readme_type;
    ALTER TABLE packages DROP COLUMN readme_needs_to_be_processed;
END;
