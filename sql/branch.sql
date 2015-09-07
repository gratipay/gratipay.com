BEGIN;
    ALTER TABLE participants DROP COLUMN status_of_1_0_balance;
    DROP TRIGGER update_status_of_1_0_balance ON participants;
    DROP FUNCTION set_status_of_1_0_balance_to_resolved();

    DROP TABLE numbers_1_0;
    DROP TABLE receivers_1_0;
END;
