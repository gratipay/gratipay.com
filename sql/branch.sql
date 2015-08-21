BEGIN;

    ALTER TABLE teams ADD COLUMN onboarding_url text NOT NULL DEFAULT '';
    ALTER TABLE teams ADD COLUMN todo_url text NOT NULL DEFAULT '';

    UPDATE teams
       SET onboarding_url='http://inside.gratipay.com/big-picture/welcome'
         , todo_url='https://github.com/gratipay'
     WHERE slug='Gratipay';

END;
