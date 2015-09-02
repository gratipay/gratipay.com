SELECT * FROM (

    SELECT DISTINCT ON (tippee)
           tippee
         , balance
         , ( SELECT sum(amount)
               FROM payments
              WHERE participant = tippee
                AND "timestamp" > '2015-05-07'::timestamptz
                AND direction='to-team'
            ) AS recent_payments
         , ( SELECT sum(amount)
               FROM payments
              WHERE participant = tippee
                AND "timestamp" > '2015-05-07'::timestamptz
                AND direction='to-participant'
            ) AS recent_payroll
      FROM transfers t
      JOIN participants p ON t.tippee = p.username
     WHERE "timestamp" < '2015-05-07'::timestamptz
       AND balance > 0
) AS _

WHERE (recent_payments IS NOT NULL) OR (recent_payroll IS NOT NULL)
ORDER BY recent_payments DESC, recent_payroll DESC, balance DESC;
