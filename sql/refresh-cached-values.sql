    -- reset caches on teams
    WITH all_receiving AS (
        SELECT amount, team
          FROM current_payment_instructions
          JOIN participants p ON p.username = participant
           AND p.is_suspicious IS NOT true
           AND amount > 0
           AND is_funded
    )
    UPDATE teams t
       SET receiving = COALESCE((SELECT sum(amount) FROM all_receiving WHERE slug=team), 0)
         , nreceiving_from = COALESCE((SELECT count(*) FROM all_receiving WHERE slug=team), 0)
         , distributing = COALESCE((SELECT sum(amount) FROM all_receiving WHERE slug=team), 0)
         , ndistributing_to = 1;


    -- reset caches on participants
    WITH pi AS (
        SELECT amount, participant
          FROM current_payment_instructions cpi
          JOIN teams t ON t.slug = cpi.team
           AND amount > 0
           AND is_funded
           AND t.is_approved
    )
    UPDATE participants p
       SET giving = COALESCE((SELECT sum(amount) FROM pi WHERE participant=username), 0)
         , ngiving_to = COALESCE((SELECT count(amount) FROM pi WHERE participant=username), 0)
         , taking=COALESCE((SELECT sum(receiving) FROM teams WHERE owner=username), 0)
         , ntaking_from=COALESCE((SELECT count(*) FROM teams WHERE owner=username), 0);

    -- Double-check
    SELECT name, receiving, nreceiving_from, distributing, ndistributing_to
      FROM teams WHERE slug='Gratipay';
    SELECT username, giving, ngiving_to, taking, ntaking_from
      FROM participants WHERE username='Gratipay';
    SELECT username, giving, ngiving_to, taking, ntaking_from
      FROM participants WHERE username='whit537';

