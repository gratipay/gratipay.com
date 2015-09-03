UPDATE numbers_1_0 SET at_gratipocalypse =
    (balance - paid_in + paid_out - transferred_to + transferred_from - paid_to + paid_from);
UPDATE numbers_1_0 SET remaining =
    (at_gratipocalypse - paid_out - transferred_from - paid_from);
