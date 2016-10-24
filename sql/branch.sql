BEGIN;

    CREATE TABLE packages
    ( id                    bigserial                   PRIMARY KEY
    , package_manager       text                        NOT NULL
    , name                  text                        NOT NULL
    , description           text                        NOT NULL
    , long_description      text                        NOT NULL DEFAULT ''
    , long_description_raw  text                        NOT NULL DEFAULT ''
    , long_description_type text                        NOT NULL DEFAULT ''
    , emails                text[]                      NOT NULL
    , UNIQUE (package_manager, name)
     );

END;
