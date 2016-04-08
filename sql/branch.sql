BEGIN;
    UPDATE payment_instructions SET due = 0 WHERE amount = 0 AND due != 0;

    UPDATE payment_instructions pi
       SET due = 0
     WHERE due > 9.41
       AND (                          -- Doesn't have a valid CC
             SELECT COUNT(*)
               FROM current_exchange_routes r
              WHERE r.participant = (SELECT id FROM participants WHERE username = pi.participant)
                AND network = 'braintree-cc'
                AND error = ''
           ) = 0;
END;
