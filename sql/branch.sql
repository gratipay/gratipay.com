BEGIN;
    CREATE TYPE email_auth_intent AS ENUM ('sign-in');

    CREATE TABLE email_auth_nonces
    ( id                    serial                      PRIMARY KEY
    , email_address         text                        NOT NULL
    , intent                email_auth_intent           NOT NULL
    , nonce                 text                        NOT NULL
    , ctime                 timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , UNIQUE (nonce)
     );
END;
