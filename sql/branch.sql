-- https://github.com/gratipay/gratipay.com/pull/4037

BEGIN;
    DROP VIEW current_payroll;
    DROP TABLE payroll;
END;
