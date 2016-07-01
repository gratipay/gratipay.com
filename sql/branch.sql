-- https://github.com/gratipay/gratipay.com/pull/4037

BEGIN;
    DROP VIEW current_payroll;
    DROP TABLE payroll;
END;


-- https://github.com/gratipay/gratipay.com/pull/4023

BEGIN;
    DROP VIEW current_takes;
    DROP TABLE takes;

    -- takes - how participants express membership in teams
    CREATE TABLE takes
    ( id                bigserial                   PRIMARY KEY
    , ctime             timestamp with time zone    NOT NULL
    , mtime             timestamp with time zone    NOT NULL DEFAULT now()
    , participant_id    bigint                      NOT NULL REFERENCES participants(id)
    , team_id           bigint                      NOT NULL REFERENCES teams(id)
    , amount            numeric(35,2)               NOT NULL
    , recorder_id       bigint                      NOT NULL REFERENCES participants(id)
    , CONSTRAINT not_negative CHECK (amount >= 0)
     );

    CREATE VIEW current_takes AS
        SELECT * FROM (
             SELECT DISTINCT ON (participant_id, team_id) t.*
               FROM takes t
               JOIN participants p ON p.id = t.participant_id
              WHERE p.is_suspicious IS NOT TRUE
           ORDER BY participant_id
                  , team_id
                  , mtime DESC
        ) AS anon WHERE amount > 0;

END;
