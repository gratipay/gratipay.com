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
