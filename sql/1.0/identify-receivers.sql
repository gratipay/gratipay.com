DROP TABLE IF EXISTS receivers_1_0;
CREATE TABLE receivers_1_0 AS (
    SELECT DISTINCT ON (tippee)
           tippee AS participant
         , balance
      FROM transfers t
      JOIN participants p ON t.tippee = p.username
     WHERE "timestamp" < '2015-05-07'::timestamptz
       AND balance > 0
);
