DROP TABLE IF EXISTS numbers_1_0;
CREATE TABLE numbers_1_0 AS (
  SELECT r.participant
       , r.balance

       , (SELECT coalesce(sum(amount), 0) FROM exchanges
          WHERE participant=r.participant AND "timestamp" > '2015-05-07' AND amount > 0
          AND status != 'failed')           AS paid_in
       , (SELECT -coalesce(sum(amount - fee), 0) FROM exchanges
          WHERE participant=r.participant AND "timestamp" > '2015-05-07' AND amount < 0
          AND status != 'failed')           AS paid_out

       , (SELECT coalesce(sum(amount), 0) FROM transfers t
          WHERE t.tippee=r.participant AND "timestamp" > '2015-05-07')
                                            AS transferred_to
       , (SELECT coalesce(sum(amount), 0) FROM transfers t
          WHERE t.tipper=r.participant AND "timestamp" > '2015-05-07')
                                            AS transferred_from

       , (SELECT coalesce(sum(amount), 0) FROM payments p
          WHERE p.participant=r.participant AND "timestamp" > '2015-05-07'
          AND direction='to-participant')   AS paid_to
       , (SELECT coalesce(sum(amount), 0) FROM payments p
          WHERE p.participant=r.participant AND "timestamp" > '2015-05-07'
          AND direction='to-team')          AS paid_from

       , 0::numeric(35,2) AS at_gratipocalypse
       , 0::numeric(35,2) AS remaining

    FROM receivers_1_0 r
ORDER BY balance DESC, participant
);
