BEGIN;

    DROP TABLE payments;


    CREATE FUNCTION current_payday() RETURNS SETOF paydays AS $$
        SELECT *
          FROM paydays
         WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz;
    $$ LANGUAGE sql;

    CREATE FUNCTION current_payday_id() RETURNS int AS $$
        -- This is a function so we can use it in DEFAULTS for a column.
        SELECT id FROM current_payday();
    $$ LANGUAGE sql;


    -- Accounts

    CREATE TYPE account_type AS ENUM ('asset', 'liability', 'income', 'expense');

    CREATE TABLE accounts
    ( id            serial      PRIMARY KEY
    , type          account_type        NOT NULL
    , system        text        DEFAULT NULL UNIQUE
    , participant   text        DEFAULT NULL UNIQUE REFERENCES participants
                                    ON UPDATE CASCADE ON DELETE RESTRICT
    , team          text        DEFAULT NULL UNIQUE REFERENCES teams
                                    ON UPDATE CASCADE ON DELETE RESTRICT

    , CONSTRAINT exactly_one_foreign_key CHECK (
        CASE WHEN system        IS NULL THEN 0 ELSE 1 END +
        CASE WHEN participant   IS NULL THEN 0 ELSE 1 END +
        CASE WHEN team          IS NULL THEN 0 ELSE 1 END = 1
      )
     );

    CREATE FUNCTION create_system_accounts() RETURNS void AS $$
    BEGIN
        INSERT INTO accounts (type, system) VALUES ('asset', 'cash');
        INSERT INTO accounts (type, system) VALUES ('asset', 'accounts receivable');
        INSERT INTO accounts (type, system) VALUES ('liability', 'accounts payable');
        INSERT INTO accounts (type, system) VALUES ('income', 'processing fee revenues');
        INSERT INTO accounts (type, system) VALUES ('expense', 'processing fee expenses');
        INSERT INTO accounts (type, system) VALUES ('income', 'earned interest');
        INSERT INTO accounts (type, system) VALUES ('expense', 'chargeback expenses');
    END;
    $$ LANGUAGE plpgsql;
    SELECT create_system_accounts();


    CREATE FUNCTION create_account_for_participant() RETURNS trigger AS $$
    BEGIN
        INSERT INTO accounts (type, participant) VALUES ('liability', NEW.username);
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER create_account_for_participant AFTER INSERT ON participants
        FOR EACH ROW EXECUTE PROCEDURE create_account_for_participant();


    CREATE FUNCTION create_account_for_team() RETURNS trigger AS $$
    BEGIN
        INSERT INTO accounts (type, team) VALUES ('liability', NEW.slug);
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER create_account_for_team AFTER INSERT ON teams
        FOR EACH ROW EXECUTE PROCEDURE create_account_for_team();


    -- The Journal

    CREATE TABLE journal
    ( id        bigserial           PRIMARY KEY
    , ts        timestamptz         NOT NULL DEFAULT CURRENT_TIMESTAMP
    , amount    numeric(35, 2)      NOT NULL
    , debit     bigint              NOT NULL REFERENCES accounts
    , credit    bigint              NOT NULL REFERENCES accounts
    , payday    int                 DEFAULT NULL REFERENCES paydays
    , route     bigint              DEFAULT NULL REFERENCES exchange_routes
    , status    exchange_status     DEFAULT NULL
    , recorder  text                DEFAULT NULL REFERENCES participants
                                        ON UPDATE CASCADE ON DELETE RESTRICT
     );

    CREATE FUNCTION update_balance() RETURNS trigger AS $$
    DECLARE
        to_debit    text;
        to_credit   text;
        to_update   text;
        delta       numeric(35, 2);
    BEGIN

        to_debit = (SELECT participant FROM accounts WHERE id=NEW.debit);
        to_credit = (SELECT participant FROM accounts WHERE id=NEW.credit);

        IF (to_debit IS NULL) AND (to_credit IS NULL) THEN
            -- No participants involved in this journal entry.
            RETURN NULL;
        END IF;

        IF (to_debit IS NOT NULL) AND (to_credit IS NOT NULL) THEN
            -- Two participants involved in this journal entry!
            -- This is a bug: we don't allow direct transfers from one ~user to another.
            RAISE USING MESSAGE =
                'Both ' || to_debit || ' and ' || to_credit || ' are participants.';
        END IF;

        IF to_debit IS NOT NULL THEN
            -- Debiting a liability decreases it.
            to_update = to_debit;
            delta = -NEW.amount;
        ELSE
            -- Crediting a liability increases it.
            to_update = to_credit;
            delta = NEW.amount;
        END IF;

        UPDATE participants SET balance = balance + delta WHERE username=to_update;

        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_balance AFTER INSERT ON journal
        FOR EACH ROW EXECUTE PROCEDURE update_balance();


    -- Journal Notes

    CREATE TABLE journal_notes
    ( id            bigserial       PRIMARY KEY
    , body          text            NOT NULL
    , author        text            NOT NULL REFERENCES participants
                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , is_private    boolean         NOT NULL DEFAULT TRUE
     );

END;
