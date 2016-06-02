-- https://github.com/gratipay/gratipay.com/pull/4046

BEGIN;

    ALTER TABLE payment_instructions ADD COLUMN participant_id bigint DEFAULT NULL
       REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
    ALTER TABLE payment_instructions ADD COLUMN team_id bigint DEFAULT NULL
       REFERENCES teams(id) ON UPDATE RESTRICT ON DELETE RESTRICT;

    DROP VIEW current_payment_instructions;

    UPDATE payment_instructions AS pi
       SET participant_id = p.id
      FROM participants AS p
     WHERE p.username = pi.participant
       AND pi.participant_id IS NULL;

    UPDATE payment_instructions AS pi
       SET team_id = t.id
      FROM teams AS t
     WHERE t.slug = pi.team
       AND pi.team_id IS NULL;

    ALTER TABLE payment_instructions DROP COLUMN participant;
    ALTER TABLE payment_instructions DROP COLUMN team;

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
