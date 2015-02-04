BEGIN;
    ALTER TABLE participants    ADD COLUMN public_giving        boolean NOT NULL DEFAULT TRUE;
    ALTER TABLE participants    ADD COLUMN public_receiving     boolean NOT NULL DEFAULT TRUE;
    ALTER TABLE participants    ADD COLUMN public_supporting    boolean NOT NULL DEFAULT FALSE;
    ALTER TABLE participants    ADD COLUMN public_supporters    boolean NOT NULL DEFAULT FALSE;

    ALTER TABLE participants    ADD COLUMN tell_supporting      boolean NOT NULL DEFAULT FALSE;

    ALTER TABLE participants    ADD COLUMN know_supporters      boolean DEFAULT FALSE;

    UPDATE participants SET public_receiving=not anonymous_receiving
                          , public_giving=not anonymous_giving;

    ALTER TABLE participants    DROP COLUMN anonymous_receiving;
    ALTER TABLE participants    DROP COLUMN anonymous_giving;

    ALTER TABLE tips            ADD COLUMN show_tippee          boolean NOT NULL DEFAULT FALSE;
    ALTER TABLE tips            ADD COLUMN show_everyone        boolean NOT NULL DEFAULT FALSE;
END;
