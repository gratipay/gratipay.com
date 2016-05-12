-- https://github.com/gratipay/gratipay.com/pull/4009

BEGIN;
    -- Farewell, old takes table!
    DROP VIEW current_takes;
    DROP TABLE takes;

    -- Be gone, payroll! I never knew you.
    DROP VIEW current_payroll;
    DROP TABLE payroll;
END;


-- https://github.com/gratipay/gratipay.com/pull/4023

BEGIN;

    -- takes - how participants express membership in teams
    CREATE TABLE takes
    ( id                bigserial                   PRIMARY KEY
    , ctime             timestamp with time zone    NOT NULL
    , mtime             timestamp with time zone    NOT NULL DEFAULT now()
    , participant_id    bigint                      NOT NULL REFERENCES participants(id)
    , team_id           bigint                      NOT NULL REFERENCES teams(id)
    , ntakes            bigint                      NOT NULL
    , recorder_id       bigint                      NOT NULL REFERENCES participants(id)
    , CONSTRAINT not_negative CHECK (ntakes >= 0)
     );

    CREATE VIEW memberships AS
        SELECT * FROM (
             SELECT DISTINCT ON (participant_id, team_id) t.*
               FROM takes t
               JOIN participants p ON p.id = t.participant_id
              WHERE p.is_suspicious IS NOT TRUE
           ORDER BY participant_id
                  , team_id
                  , mtime DESC
        ) AS anon WHERE ntakes > 0;

    ALTER TABLE teams ADD COLUMN ntakes bigint default 0;
    ALTER TABLE teams ADD COLUMN ntakes_unclaimed bigint default 0;
    ALTER TABLE teams ADD COLUMN ntakes_claimed bigint default 0;
    ALTER TABLE teams ADD CONSTRAINT ntakes_sign CHECK (ntakes >= 0);
    ALTER TABLE teams ADD CONSTRAINT ntakes_sum CHECK (ntakes = ntakes_claimed + ntakes_unclaimed);

END;


-- https://github.com/gratipay/gratipay.com/pull/4025

ALTER TABLE teams ADD COLUMN baseline numeric(35,2) NOT NULL DEFAULT 0.0;
