BEGIN;

    ALTER TABLE teams DROP COLUMN revenue_model;
    ALTER TABLE teams DROP COLUMN getting_involved;
    ALTER TABLE teams DROP COLUMN getting_paid;

    ALTER TABLE teams ADD COLUMN todo_url text NOT NULL DEFAULT '';
    ALTER TABLE teams ADD COLUMN onboarding_url text NOT NULL DEFAULT '';

    UPDATE teams
       SET todo_url='https://github.com/gratipay'
         , onboarding_url='http://inside.gratipay.com/big-picture/welcome'
     WHERE slug='Gratipay';

END;
