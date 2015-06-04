BEGIN;
    CREATE TABLE team_memberships
    ( id               serial                       PRIMARY KEY
    , member           text                         NOT NULL REFERENCES participants
                                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , team             text                         NOT NULL REFERENCES teams
                                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , is_active        boolean                      DEFAULT NULL
    , ctime            timestamp with time zone     NOT NULL
    , mtime            timestamp with time zone     NOT NULL DEFAULT CURRENT_TIMESTAMP
    , UNIQUE (team, member)
     );
END;
