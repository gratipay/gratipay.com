BEGIN;

    -- teams - the entity that can receive and distribute payments
    CREATE TABLE teams
    ( slug                  text                        PRIMARY KEY
    , id                    bigserial                   NOT NULL UNIQUE
    , ctime                 timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , slug_lower            text                        NOT NULL UNIQUE
    , name                  text                        NOT NULL
    , homepage              text                        NOT NULL
    , product_or_service    text                        NOT NULL
    , getting_involved      text                        NOT NULL
    , getting_paid          text                        NOT NULL
    , owner                 text                        NOT NULL REFERENCES participants
                                                            ON UPDATE CASCADE ON DELETE RESTRICT
    , is_closed             boolean                     NOT NULL DEFAULT FALSE
    , is_approved           boolean                     DEFAULT NULL
    , receiving             numeric(35,2)               NOT NULL DEFAULT 0
    , nsupporters           integer                     NOT NULL DEFAULT 0
    , payroll               numeric(35,2)               NOT NULL DEFAULT 0
    , nmembers              integer                     NOT NULL DEFAULT 0
     );

END;
