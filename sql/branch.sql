BEGIN;
    \i sql/1.0/all.sql

    CREATE TYPE status_of_1_0_payout AS ENUM
        ('pending-application', 'pending-review', 'rejected', 'pending-payout', 'completed');
    ALTER TABLE participants ADD COLUMN status_of_1_0_payout status_of_1_0_payout
        NOT NULL DEFAULT 'completed';

    UPDATE participants
       SET status_of_1_0_payout = 'pending-application'
     WHERE username = ANY(SELECT participant FROM numbers_1_0 WHERE remaining > 0);

    UPDATE participants
       SET status_of_1_0_payout='pending-payout'
     WHERE status_of_1_0_balance='pending-payout';

    UPDATE participants
       SET status_of_1_0_payout='completed'
     WHERE status_of_1_0_balance='resolved';

    ALTER TABLE participants DROP COLUMN status_of_1_0_balance;
    DROP TRIGGER update_status_of_1_0_balance ON participants;
    DROP FUNCTION set_status_of_1_0_balance_to_resolved();

    CREATE FUNCTION complete_1_0_payout() RETURNS trigger AS $$
        BEGIN
            UPDATE participants
               SET status_of_1_0_payout='completed'
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_status_of_1_0_payout
        AFTER UPDATE OF balance ON participants
        FOR EACH ROW
        WHEN (OLD.balance > 0 AND NEW.balance = 0)
        EXECUTE PROCEDURE complete_1_0_payout();
END;
