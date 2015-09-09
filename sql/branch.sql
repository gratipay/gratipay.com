BEGIN;
    CREATE TYPE supported_image_types AS ENUM ('image/png', 'image/gif', 'image/jpeg');
    CREATE TABLE team_images
    ( id            bigint                  primary key references teams (id)
    , data          bytea                   NOT NULL
    , media_type    supported_image_types   NOT NULL
     );
END;
