BEGIN;
    UPDATE payment_instructions SET due = 0 WHERE due > 9.41;
END;
