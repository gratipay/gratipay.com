-- Manually correct two users per https://github.com/gratipay/gratipay.com/issues/3453
-- The other two affected users there currently have a zero balance, so they're
-- not included in receiving_1_0 (any Gratipay 1.0 money they accumulated is
-- already gone).

UPDATE numbers_1_0
   SET paid_in = paid_in - paid_out, paid_out = 0
 WHERE participant IN ('webmaven', 'whit537');


-- Compute balance at the Gratipocalypse, and 1.0 balance that remains.

UPDATE numbers_1_0 SET at_gratipocalypse =
    (balance - paid_in + paid_out - transferred_to + transferred_from - paid_to + paid_from);
UPDATE numbers_1_0 SET remaining =
    (at_gratipocalypse - paid_out - transferred_from - paid_from);
