BEGIN;

    CREATE TABLE packages
    ( id                bigserial   PRIMARY KEY
    , package_manager   text        NOT NULL
    , name              text        NOT NULL
    , description       text        NOT NULL
    , readme            text        NOT NULL DEFAULT ''
    , readme_raw        text        NOT NULL DEFAULT ''
    , readme_type       text        NOT NULL DEFAULT ''
    , emails            text[]      NOT NULL
    , UNIQUE (package_manager, name)
     );

END;
