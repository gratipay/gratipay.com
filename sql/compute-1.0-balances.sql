DROP TABLE IF EXISTS numbers_1_0;
CREATE TABLE numbers_1_0 AS (
  SELECT *
       , (SELECT coalesce(sum(amount), 0) FROM exchanges
          WHERE participant=r.participant AND "timestamp" > '2015-05-07' AND amount > 0
          AND status != 'failed') AS paid_in
       , (SELECT -coalesce(sum(amount - fee), 0) FROM exchanges
          WHERE participant=r.participant AND "timestamp" > '2015-05-07' AND amount < 0
          AND status != 'failed') AS paid_out

       , (SELECT coalesce(sum(amount), 0) FROM transfers t
          WHERE t.tippee=r.participant AND "timestamp" > '2015-05-07') AS tips_to
       , (SELECT coalesce(sum(amount), 0) FROM transfers t
          WHERE t.tipper=r.participant AND "timestamp" > '2015-05-07') AS tips_from

       , (SELECT coalesce(sum(amount), 0) FROM payments p
          WHERE p.participant=r.participant AND "timestamp" > '2015-05-07' AND direction='to-team') AS giving
       , (SELECT coalesce(sum(amount), 0) FROM payments p
          WHERE p.participant=r.participant AND "timestamp" > '2015-05-07' AND direction='to-participant') AS taking
       , 0::numeric(35,2) AS balance_gratipocalypse
    FROM receivers_1_0 r
ORDER BY balance DESC, participant
);

UPDATE numbers_1_0 SET balance_gratipocalypse =
    (balance - paid_in + paid_out - tips_to + tips_from + giving - taking);

DELETE FROM numbers_1_0 WHERE balance_gratipocalypse = 0;
