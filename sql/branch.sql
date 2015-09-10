BEGIN;
    CREATE TYPE supported_image_types AS ENUM ('image/png', 'image/gif', 'image/jpeg');
    ALTER TABLE teams ADD COLUMN image_oid oid NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD COLUMN image_type supported_image_types;
END;
