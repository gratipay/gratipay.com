BEGIN;
    UPDATE payment_instructions SET due = 0 WHERE amount = 0 AND due != 0;
    UPDATE payment_instructions SET due = floor(9.41/(amount)) * amount WHERE due > 9.41;
    CREATE TABLE settings (minimum_charge numeric(35,2) DEFAULT NULL);
END;
