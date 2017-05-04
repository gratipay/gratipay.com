-- A bug was discovered in https://github.com/gratipay/gratipay.com/pull/4439
-- Let's delete all cached entries in the table, they'll be regenerated with proper values.
DELETE FROM balances_at;
