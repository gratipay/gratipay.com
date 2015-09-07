BEGIN;

    ALTER TABLE payment_instructions ADD COLUMN due numeric(35,2) DEFAULT 0;

    -- Recreate the current_payment_instructions view to pick up due.
    DROP VIEW current_payment_instructions;
    CREATE VIEW current_payment_instructions AS
        SELECT DISTINCT ON (participant, team) *
          FROM payment_instructions
      ORDER BY participant, team, mtime DESC;

    -- Allow updating is_funded and due via the current_payment_instructions view for convenience.
    DROP FUNCTION update_payment_instruction();
    CREATE FUNCTION update_payment_instruction() RETURNS trigger AS $$
        BEGIN
            UPDATE payment_instructions
               SET is_funded = NEW.is_funded
                 , due = NEW.due
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_current_payment_instruction
        INSTEAD OF UPDATE ON current_payment_instructions
        FOR EACH ROW EXECUTE PROCEDURE update_payment_instruction();
END;
