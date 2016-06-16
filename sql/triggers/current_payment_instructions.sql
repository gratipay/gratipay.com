CREATE FUNCTION update_current_payment_instructions()
RETURNS trigger AS $$
BEGIN

    -- Allow updating is_funded and due via the current_payment_instructions view for convenience.
    UPDATE payment_instructions
       SET is_funded = NEW.is_funded
         , due = NEW.due
     WHERE id = NEW.id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER update_current_payment_instructions
    INSTEAD OF UPDATE ON current_payment_instructions
    FOR EACH ROW EXECUTE PROCEDURE update_current_payment_instructions();
