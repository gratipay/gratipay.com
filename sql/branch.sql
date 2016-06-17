BEGIN;

    DROP VIEW current_payment_instructions;

    ALTER TABLE payment_instructions DROP COLUMN participant;
    ALTER TABLE payment_instructions DROP COLUMN team;

    CREATE VIEW current_payment_instructions AS
        SELECT DISTINCT ON (participant_id, team_id) *
          FROM payment_instructions
      ORDER BY participant_id, team_id, mtime DESC;

    CREATE TRIGGER update_current_payment_instruction
        INSTEAD OF UPDATE ON current_payment_instructions
        FOR EACH ROW EXECUTE PROCEDURE update_payment_instruction();

END;
