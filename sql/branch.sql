BEGIN;

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

END;
