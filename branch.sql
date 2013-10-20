CREATE INDEX participants_claimed_time ON participants (claimed_time DESC) 
  WHERE is_suspicious IS NOT TRUE 
    AND claimed_time IS NOT null;

DROP TABLE homepage_new_participants;

CREATE OR REPLACE FUNCTION receiving(v_username text) RETURNS NUMERIC(35,2) AS $$
    DECLARE
        ret numeric(35,2);
    BEGIN
        SELECT INTO ret sum(amount)
              FROM ( SELECT DISTINCT ON (tipper)
                             amount
                           , tipper
                        FROM tips
                        JOIN participants p ON p.username = tipper
                       WHERE tippee=v_username
                         AND last_bill_result = ''
                         AND is_suspicious IS NOT true
                    ORDER BY tipper
                            , mtime DESC
                        ) AS foo;
        RETURN ret;
    END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION giving(v_username text) RETURNS NUMERIC(35,2) AS $$
    DECLARE
        ret numeric(35,2);
    BEGIN
        SELECT INTO ret sum(amount)
              FROM ( SELECT DISTINCT ON (tippee)
                            amount
                          , tippee
                       FROM tips
                       JOIN participants p ON p.username = tippee
                      WHERE tipper=v_username
                        AND is_suspicious IS NOT true
                        AND claimed_time IS NOT NULL
                   ORDER BY tippee
                          , mtime DESC
                    ) AS foo;
        RETURN ret;
    END;
$$ LANGUAGE plpgsql;

BEGIN;
    ALTER TABLE participants ADD COLUMN receiving numeric(35,2) DEFAULT 0.00;
    ALTER TABLE participants ADD COLUMN giving    numeric(35,2) DEFAULT 0.00;

    UPDATE participants SET receiving = receiving(username), giving = giving(username);
    
    -- receiving
    CREATE FUNCTION update_receiving() RETURNS TRIGGER AS $$
    BEGIN
        UPDATE participants SET receiving = receiving(NEW.tippee) WHERE username = NEW.tippee;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    CREATE TRIGGER update_receiving AFTER INSERT ON tips
        FOR EACH ROW EXECUTE PROCEDURE update_receiving();

    -- giving
    CREATE FUNCTION update_giving() RETURNS TRIGGER AS $$
    BEGIN
        UPDATE participants SET giving = giving(NEW.tipper) WHERE username = NEW.tipper;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    CREATE TRIGGER update_giving_trigger AFTER INSERT ON tips
        FOR EACH ROW EXECUTE PROCEDURE update_giving();
END;

CREATE INDEX participants_receiving ON participants (receiving DESC);
CREATE INDEX participants_giving    ON participants (giving DESC);
