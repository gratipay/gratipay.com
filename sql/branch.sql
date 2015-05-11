BEGIN;

    -- teams - the entity that can receive payments and distribute payroll
    CREATE TABLE teams
    ( slug                  text                        PRIMARY KEY
    , id                    bigserial                   NOT NULL UNIQUE
    , ctime                 timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , display_name          text                        NOT NULL
    , slug_lower            text                        NOT NULL UNIQUE
    , homepage              text                        NOT NULL
    , product_or_service    text                        NOT NULL
    , getting_involved      text                        NOT NULL
    , getting_paid          text                        NOT NULL
    , owner                 text                        NOT NULL REFERENCES participants
                                                            ON UPDATE CASCADE ON DELETE RESTRICT
    , is_approved           boolean                     DEFAULT NULL
    , receiving             numeric(35,2)               NOT NULL DEFAULT 0
    , nsupporters           integer                     NOT NULL DEFAULT 0
    , payroll               numeric(35,2)               NOT NULL DEFAULT 0
    , npayroll              integer                     NOT NULL DEFAULT 0
     );


    -- subscriptions - recurring payments from a participant to a team
    CREATE TABLE subscriptions
    ( id                    serial                      PRIMARY KEY
    , ctime                 timestamp with time zone    NOT NULL
    , mtime                 timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , subscriber            text                        NOT NULL REFERENCES participants
                                                            ON UPDATE CASCADE ON DELETE RESTRICT
    , team                  text                        NOT NULL REFERENCES teams
                                                            ON UPDATE CASCADE ON DELETE RESTRICT
    , amount                numeric(35,2)               NOT NULL
    , is_funded             boolean                     NOT NULL DEFAULT false
     );

    CREATE INDEX subscriptions_all ON subscriptions USING btree (subscriber, team, mtime DESC);

    CREATE VIEW current_subscriptions AS
        SELECT DISTINCT ON (subscriber, team) *
          FROM subscriptions
      ORDER BY subscriber, team, mtime DESC;

    -- Allow updating is_funded via the current_subscriptions view for convenience
    CREATE FUNCTION update_subscription() RETURNS trigger AS $$
        BEGIN
            UPDATE subscriptions
               SET is_funded = NEW.is_funded
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER update_current_subscription INSTEAD OF UPDATE ON current_subscriptions
        FOR EACH ROW EXECUTE PROCEDURE update_subscription();


    -- payroll - recurring payments from a team to participant
    CREATE TABLE payroll
    ( id                serial                      PRIMARY KEY
    , ctime             timestamp with time zone    NOT NULL
    , mtime             timestamp with time zone    NOT NULL
                                                    DEFAULT CURRENT_TIMESTAMP
    , recipient         text                        NOT NULL REFERENCES participants
                                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , team              text                        NOT NULL REFERENCES teams
                                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , amount            numeric(35,2)               NOT NULL DEFAULT 0.0
    , recorder          text                        NOT NULL REFERENCES participants
                                                        ON UPDATE CASCADE ON DELETE RESTRICT
    , CONSTRAINT not_negative CHECK ((amount >= (0)::numeric))
     );

    CREATE VIEW current_payroll AS
        SELECT * FROM (
             SELECT DISTINCT ON (recipient, team) payroll.*
               FROM payroll
               JOIN participants p ON p.username = payroll.recipient
              WHERE p.is_suspicious IS NOT TRUE
           ORDER BY recipient
                  , team
                  , mtime DESC
        ) AS anon WHERE amount > 0;

END;
