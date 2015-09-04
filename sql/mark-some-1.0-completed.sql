BEGIN;

    UPDATE participants
       SET status_of_1_0_payout = 'completed'
     WHERE username =ANY(SELECT participant FROM numbers_1_0 WHERE remaining <= 0);

END;
