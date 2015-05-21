BEGIN;

    ALTER TABLE participant ADD COLUMN braintree_id text NOT NULL DEFAULT '';

END;
