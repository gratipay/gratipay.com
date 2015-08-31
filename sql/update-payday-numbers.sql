-- Fix nusers and backfill nteams for post-Gratipocalypse paydays
UPDATE paydays p
   SET nteams = (SELECT count(*) FROM (
        SELECT DISTINCT ON (team) team FROM payments WHERE payday=p.id GROUP BY team
       ) AS foo)
     , nusers = (SELECT count(*) FROM (
        SELECT DISTINCT ON (participant) participant FROM payments WHERE payday=p.id GROUP BY participant
       ) AS foo)
 WHERE ts_start > '2015-05-07'::timestamptz;
