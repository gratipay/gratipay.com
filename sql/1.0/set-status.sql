UPDATE participants
   SET status_of_1_0_payout = 'pending-application'
 WHERE username = ANY(SELECT participant FROM numbers_1_0 WHERE remaining > 0);

UPDATE participants
   SET status_of_1_0_payout='pending-payout'
 WHERE status_of_1_0_balance='pending-payout';

UPDATE participants
   SET status_of_1_0_payout='completed'
 WHERE status_of_1_0_balance='resolved';

UPDATE participants
   SET status_of_1_0_payout = 'too-little'
 WHERE status_of_1_0_payout = 'pending-application' and balance < 0.50;
