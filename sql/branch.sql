BEGIN;

    CREATE TABLE packages
    ( id                    bigserial                   PRIMARY KEY
    , package_manager       text                        NOT NULL
    , name                  text                        NOT NULL
    , description           text                        NOT NULL DEFAULT ''
    , long_description      text                        NOT NULL DEFAULT ''
    , long_description_raw  text                        NOT NULL DEFAULT ''
    , long_description_type text                        NOT NULL DEFAULT ''
    , mtime                 timestamp with time zone    NOT NULL
    , UNIQUE (package_manager, name)
     );

    CREATE TABLE package_emails
    ( id            bigserial   PRIMARY KEY
    , package_id    bigint      NOT NULL REFERENCES packages ON UPDATE CASCADE ON DELETE RESTRICT
    , email         text        NOT NULL
    , UNIQUE (package_id, email)
     );

END;
