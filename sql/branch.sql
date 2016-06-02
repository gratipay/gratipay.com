BEGIN;  -- Step 1

    ALTER TABLE payment_instructions ADD COLUMN participant_id bigint DEFAULT NULL
       REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
    ALTER TABLE payment_instructions ADD COLUMN team_id bigint DEFAULT NULL
       REFERENCES teams(id) ON UPDATE RESTRICT ON DELETE RESTRICT;

END;


BEGIN;  -- Step 2

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


BEGIN;  -- Step 3

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


-- https://github.com/gratipay/gratipay.com/pull/4045

\i sql/triggers/payment_instructions.sql

DROP FUNCTION update_payment_instruction();
\i sql/triggers/current_payment_instructions.sql
