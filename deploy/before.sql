BEGIN;
    ALTER TABLE payments_for_open_source ADD COLUMN on_mailing_list bool NOT NULL DEFAULT TRUE;
    UPDATE payments_for_open_source SET on_mailing_list=false WHERE follow_up = 'never';
    ALTER TABLE payments_for_open_source DROP COLUMN follow_up;
END;
