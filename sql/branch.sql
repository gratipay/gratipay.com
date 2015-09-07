BEGIN;
    ALTER TABLE participants DROP COLUMN status_of_1_0_balance;
    DROP TRIGGER update_status_of_1_0_balance ON participants;
    DROP FUNCTION set_status_of_1_0_balance_to_resolved();
END;
