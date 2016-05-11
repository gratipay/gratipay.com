-- participants.has_verified_identity

ALTER TABLE participants ADD COLUMN has_verified_identity bool NOT NULL DEFAULT false;
