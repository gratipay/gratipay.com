-- https://github.com/gratipay/gratipay.com/pull/4072

BEGIN;
    ALTER TABLE teams ADD COLUMN available numeric(35,2) NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD CONSTRAINT available_not_negative CHECK ((available >= (0)::numeric));
END;


-- https://github.com/gratipay/gratipay.com/pull/4074

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
