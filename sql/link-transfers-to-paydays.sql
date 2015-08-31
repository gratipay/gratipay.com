BEGIN;
    ALTER TABLE transfers DROP CONSTRAINT positive;
    UPDATE transfers t
       SET payday = (SELECT id
                       FROM paydays p
                      WHERE t."timestamp" > p.ts_start
                        AND t."timestamp" < p.ts_end
                     )
     WHERE context IN ('tip', 'take');
    ALTER TABLE transfers ADD CONSTRAINT positive CHECK (amount > 0) NOT VALID;
END;
