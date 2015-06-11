BEGIN;

    CREATE TYPE status_of_1_0_balance AS ENUM
        ('unresolved', 'pending-payout', 'resolved');

    ALTER TABLE participants
        ADD COLUMN status_of_1_0_balance status_of_1_0_balance
        NOT NULL
        DEFAULT 'unresolved';

    CREATE FUNCTION set_status_of_1_0_balance_to_resolved() RETURNS trigger AS $$
        BEGIN
            UPDATE participants
               SET status_of_1_0_balance='resolved'
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_status_of_1_0_balance
        AFTER UPDATE OF balance ON participants
        FOR EACH ROW
        WHEN (OLD.balance > 0 AND NEW.balance = 0)
        EXECUTE PROCEDURE set_status_of_1_0_balance_to_resolved();

END;
