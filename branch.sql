BEGIN;
    ALTER TABLE participants ADD COLUMN last_coinbase_result text DEFAULT NULL;
END;
