BEGIN;

    -- https://github.com/gratipay/inside.gratipay.com/issues/117
    -- payment_instructions - A user instructs Gratipay to make voluntary payments to a Team.
    ALTER TABLE subscriptions RENAME COLUMN subscriber TO participant;
    ALTER TABLE subscriptions RENAME CONSTRAINT subscriptions_subscriber_fkey
                                             TO payment_instructions_participant_fkey;
    ALTER TABLE subscriptions RENAME CONSTRAINT subscriptions_team_fkey
                                             TO payment_instructions_team_fkey;
    ALTER TABLE subscriptions RENAME TO payment_instructions;
    ALTER INDEX subscriptions_pkey RENAME TO payment_instructions_pkey;
    ALTER INDEX subscriptions_all RENAME TO payment_instructions_all;
    ALTER SEQUENCE subscriptions_id_seq RENAME TO payment_instructions_id_seq;

    DROP TRIGGER update_current_subscription ON current_subscriptions;
    DROP VIEW current_subscriptions;
    CREATE VIEW current_payment_instructions AS
        SELECT DISTINCT ON (participant, team) *
          FROM payment_instructions
      ORDER BY participant, team, mtime DESC;

    -- Allow updating is_funded via the current_payment_instructions view for convenience
    DROP FUNCTION update_subscription();
    CREATE FUNCTION update_payment_instruction() RETURNS trigger AS $$
        BEGIN
            UPDATE payment_instructions
               SET is_funded = NEW.is_funded
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_current_payment_instruction
    INSTEAD OF UPDATE ON current_payment_instructions
        FOR EACH ROW EXECUTE PROCEDURE update_payment_instruction();

END;
