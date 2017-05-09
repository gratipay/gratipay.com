BEGIN;

    ALTER TABLE emails ADD CONSTRAINT emails_nonce_key UNIQUE (nonce);
    CREATE TABLE claims
    ( nonce         text    NOT NULL REFERENCES emails(nonce)   ON DELETE CASCADE
                                                                ON UPDATE RESTRICT
    , package_id    bigint  NOT NULL REFERENCES packages(id)    ON DELETE RESTRICT
                                                                ON UPDATE RESTRICT
    , UNIQUE(nonce, package_id)
     );

    CREATE TABLE teams_to_packages
    ( team_id       bigint UNIQUE REFERENCES teams(id) ON DELETE RESTRICT
    , package_id    bigint UNIQUE REFERENCES packages(id) ON DELETE RESTRICT
     );

END;
