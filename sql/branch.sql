BEGIN;

    ALTER TABLE paydays RENAME COLUMN nactive TO nusers;
    ALTER TABLE paydays ADD COLUMN nteams integer NOT NULL DEFAULT 0;

END;
