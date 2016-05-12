-- https://github.com/gratipay/gratipay.com/pull/4009

BEGIN;
    -- Farewell, old takes table!
    DROP VIEW current_takes;
    DROP TABLE takes;

    -- Be gone, payroll! I never knew you.
    DROP VIEW current_payroll;
    DROP TABLE payroll;
END;
