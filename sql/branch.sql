BEGIN;

    ALTER TABLE payment_instructions ADD COLUMN participant_id bigint DEFAULT NULL
       REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
    ALTER TABLE payment_instructions ADD COLUMN team_id bigint DEFAULT NULL
       REFERENCES teams(id) ON UPDATE RESTRICT ON DELETE RESTRICT;

END;
