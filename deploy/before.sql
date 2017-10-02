BEGIN;
    ALTER TABLE payments_for_open_source ADD COLUMN id bigserial UNIQUE NOT NULL;
    ALTER TABLE payments_for_open_source ADD COLUMN image_oid_original oid NOT NULL DEFAULT 0;
    ALTER TABLE payments_for_open_source ADD COLUMN image_oid_large oid NOT NULL DEFAULT 0;
    ALTER TABLE payments_for_open_source ADD COLUMN image_oid_small oid NOT NULL DEFAULT 0;
    ALTER TABLE payments_for_open_source ADD COLUMN image_type supported_image_types;
END;
