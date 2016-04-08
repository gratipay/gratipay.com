BEGIN;
    UPDATE payment_instructions SET due = 0 WHERE amount = 0 AND due != 0;
    UPDATE payment_instructions SET due = 0 WHERE due > 9.41;
END;
