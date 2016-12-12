--https://github.com/gratipay/gratipay.com/pull/4214

BEGIN;
  ALTER TABLE teams DROP COLUMN todo_url;
END;
