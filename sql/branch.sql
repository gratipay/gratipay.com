BEGIN;

    CREATE TABLE accounts
    ( number    varchar(32)     unique not null
    , name      varchar(32)     unique not null
     );

END;
