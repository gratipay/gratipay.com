BEGIN;
    ALTER TABLE email_addresses RENAME TO email_address_to_participant;

    CREATE TABLE email_addresses
    ( address               text        NOT NULL UNIQUE
    , link_to_participant   bigint      REFERENCES email_address_to_participant(id)
     )

    -- initialize
    INSERT INTO email_verifications (address, verification) VALUES
    INSERT INTO email_addresses (address, verification) VALUES
END;
