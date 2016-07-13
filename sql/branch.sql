-- https://github.com/gratipay/gratipay.com/pull/4072

BEGIN;
    ALTER TABLE teams ADD COLUMN available numeric(35,2) NOT NULL DEFAULT 0;
    ALTER TABLE teams ADD CONSTRAINT available_not_negative CHECK ((available >= (0)::numeric));
END;
