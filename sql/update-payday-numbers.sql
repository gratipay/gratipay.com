-- Reset post-Gratipocalypse values
UPDATE paydays p
   SET nactive = (SELECT DISTINCT count(*) FROM (
        SELECT participant FROM payments WHERE payday=p.id
       ) AS foo)
     , volume = (SELECT COALESCE(sum(amount), 0)
                   FROM payments
                  WHERE payday=p.id AND direction='to-team')
 WHERE ts_start > '2015-05-07'::timestamptz;
