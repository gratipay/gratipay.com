CREATE FUNCTION propagate_payment_instructions_insert()
RETURNS trigger AS $$
DECLARE
    is_new_giver    bool;
    delta_n         int;
    delta_amount    numeric(35,2);
BEGIN
    is_new_giver := ( SELECT id
                        FROM current_payment_instructions
                       WHERE participant_id=NEW.participant_id
                         AND team_id=NEW.team_id
                         AND amount > 0
                     ) IS NULL;

    delta_amount := NEW.amount;

    IF NEW.amount = 0 THEN
        IF is_new_giver THEN
            delta_n := 0;
        ELSE
            delta_n := -1;
        END IF;
    ELSE
        IF is_new_giver THEN
            delta_n := 1;
        ELSE
            delta_n := 0;
        END IF;
    END IF;

    UPDATE participants
       SET giving = giving + delta_amount
         , ngiving_to = ngiving_to + delta_n
     WHERE id = NEW.participant_id;

    UPDATE teams
       SET receiving = receiving + delta_amount
         , nreceiving_from = nreceiving_from + delta_n
     WHERE id = NEW.team_id;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER propagate_payment_instructions_insert
    BEFORE INSERT ON payment_instructions
    FOR EACH ROW EXECUTE PROCEDURE propagate_payment_instructions_insert();
