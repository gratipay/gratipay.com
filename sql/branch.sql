ALTER TYPE payment_net ADD VALUE 'braintree-cc';

ALTER TABLE participants ADD COLUMN braintree_customer_id text DEFAULT NULL;