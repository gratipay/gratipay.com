BEGIN;
    CREATE TYPE follow_up AS ENUM ('monthly', 'quarterly', 'yearly', 'never');
    CREATE TABLE payments_for_open_source
    ( uuid      text        PRIMARY KEY
    , ctime     timestamptz NOT NULL DEFAULT now()

    -- card charge
    , amount            bigint      NOT NULL
    , transaction_id    text        UNIQUE NOT NULL

    -- contact info
    , name              text NOT NULL
    , follow_up         follow_up NOT NULL
    , email_address     text NOT NULL
    , message_id        bigint REFERENCES email_messages(id)

    -- promotion details
    , promotion_name    text NOT NULL DEFAULT ''
    , promotion_url     text NOT NULL DEFAULT ''
    , promotion_twitter text NOT NULL DEFAULT ''
    , promotion_message text NOT NULL DEFAULT ''
     );
END;
