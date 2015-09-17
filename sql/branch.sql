BEGIN;

    CREATE TABLE accounts
    ( number    varchar(32)     UNIQUE NOT NULL
    , name      varchar(32)     UNIQUE NOT NULL
     );

END;
