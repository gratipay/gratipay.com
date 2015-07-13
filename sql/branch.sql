BEGIN;

    CREATE TYPE account_type AS ENUM ('asset', 'liability', 'income', 'expense');

    CREATE TABLE accounts
    ( id            serial      PRIMARY KEY
    , type          account_type        NOT NULL
    , participant   text        DEFAULT NULL UNIQUE REFERENCES participants
                                    ON UPDATE CASCADE ON DELETE RESTRICT
    , team          text        DEFAULT NULL UNIQUE REFERENCES teams
                                    ON UPDATE CASCADE ON DELETE RESTRICT
    , system        text        DEFAULT NULL UNIQUE

    , CONSTRAINT exactly_one_foreign_key CHECK (
        CASE WHEN participant   IS NULL THEN 0 ELSE 1 END +
        CASE WHEN team          IS NULL THEN 0 ELSE 1 END +
        CASE WHEN system        IS NULL THEN 0 ELSE 1 END = 1
      )
     );

    INSERT INTO accounts (type, system) VALUES ('asset', 'escrow');
    INSERT INTO accounts (type, system) VALUES ('asset', 'escrow receivable');
    INSERT INTO accounts (type, system) VALUES ('liability', 'escrow payable');
    INSERT INTO accounts (type, system) VALUES ('income', 'processing fee revenues');
    INSERT INTO accounts (type, system) VALUES ('expense', 'processing fee expenses');
    INSERT INTO accounts (type, system) VALUES ('income', 'earned interest');
    INSERT INTO accounts (type, system) VALUES ('expense', 'chargeback expenses');


    CREATE TABLE journal
    ( id        bigserial           PRIMARY KEY
    , ts        timestamp_tz        NOT NULL DEFAULT CURRENT_TIMESTAMP
    , amount    numeric(35, 2)      NOT NULL
    , debit     bigint              NOT NULL REFERENCES accounts
    , credit    bigint              NOT NULL REFERENCES accounts
    , payday    int                 DEFAULT NULL REFERENCES paydays
    , route     bigint              DEFAULT NULL REFERENCES exchange_routes
    , status    exchange_status     DEFAULT NULL
    , recorder  text                DEFAULT NULL REFERENCES participants
                                        ON UPDATE CASCADE ON DELETE RESTRICT
     );

    CREATE TABLE journal_notes
    ( id            bigserial       PRIMARY KEY
    , body          text            NOT NULL
    , author        text            NOT NULL REFERENCES participants
                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , is_private    boolean         NOT NULL DEFAULT TRUE
     );
END;
