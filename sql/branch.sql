BEGIN;

    CREATE TABLE package_managers
    ( id        bigserial       PRIMARY KEY
    , name      text            NOT NULL UNIQUE
     );

    CREATE TABLE packages
    ( id                    bigserial                   PRIMARY KEY
    , package_manager_id    bigint                      NOT NULL
    , name                  text                        NOT NULL
    , description           text                        NOT NULL DEFAULT ''
    , long_description      text                        NOT NULL DEFAULT ''
    , long_description_raw  text                        NOT NULL DEFAULT ''
    , long_description_type text                        NOT NULL DEFAULT ''
    , mtime                 timestamp with time zone    NOT NULL
    , UNIQUE (package_manager_id, name)
     );

    CREATE TABLE package_emails
    ( package_id    bigint  NOT NULL
    , email         text    NOT NULL
    , UNIQUE (package_id, email)
     )

END;
