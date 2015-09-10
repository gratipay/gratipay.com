BEGIN;
    CREATE TYPE supported_image_types AS ENUM ('image/png', 'image/jpeg');
    ALTER TABLE teams ADD COLUMN image_oid_original oid NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD COLUMN image_oid_large oid NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD COLUMN image_oid_small oid NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD COLUMN image_type supported_image_types;
END;
