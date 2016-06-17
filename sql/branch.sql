BEGIN;

    DROP VIEW current_payment_instructions;

    UPDATE payment_instructions AS pi
       SET participant_id = (SELECT id FROM participants p WHERE p.username = pi.participant)
         , team_id = (SELECT id FROM teams t WHERE t.slug = pi.team);

    ALTER TABLE payment_instructions ALTER COLUMN participant_id SET NOT NULL;
    ALTER TABLE payment_instructions ALTER COLUMN team_id SET NOT NULL;

    CREATE VIEW current_payment_instructions AS
        SELECT DISTINCT ON (participant_id, team_id) *
          FROM payment_instructions
      ORDER BY participant_id, team_id, mtime DESC;

    CREATE TRIGGER update_current_payment_instruction
        INSTEAD OF UPDATE ON current_payment_instructions
        FOR EACH ROW EXECUTE PROCEDURE update_payment_instruction();

END;
