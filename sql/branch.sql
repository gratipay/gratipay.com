BEGIN;

    ALTER TABLE paydays DROP COLUMN nparticipants;
    ALTER TABLE paydays DROP COLUMN ntippers;
    ALTER TABLE paydays DROP COLUMN ntips;
    ALTER TABLE paydays DROP COLUMN ntransfers;
    ALTER TABLE paydays DROP COLUMN ncc_failing;
    ALTER TABLE paydays DROP COLUMN ncc_missing;
    ALTER TABLE paydays DROP COLUMN ncharges;
    ALTER TABLE paydays DROP COLUMN charge_volume;
    ALTER TABLE paydays DROP COLUMN charge_fees_volume;
    ALTER TABLE paydays DROP COLUMN nachs;
    ALTER TABLE paydays DROP COLUMN ach_volume;
    ALTER TABLE paydays DROP COLUMN ach_fees_volume;
    ALTER TABLE paydays DROP COLUMN nach_failing;
    ALTER TABLE paydays DROP COLUMN npachinko;
    ALTER TABLE paydays DROP COLUMN pachinko_volume;

    ALTER TABLE paydays RENAME COLUMN transfer_volume TO volume;
    ALTER TABLE transfers ADD COLUMN payday integer DEFAULT NULL
        REFERENCES paydays ON UPDATE RESTRICT ON DELETE RESTRICT;

END;
