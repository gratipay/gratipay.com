BEGIN;
    CREATE TYPE status_of_1_0_payout AS ENUM
        ( 'too-little'
        , 'pending-application'
        , 'pending-review'
        , 'rejected'
        , 'pending-payout'
        , 'completed'
         );
    ALTER TABLE participants ADD COLUMN status_of_1_0_payout status_of_1_0_payout
        NOT NULL DEFAULT 'completed';

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
