BEGIN;

    CREATE TYPE status_of_1_0_balance AS ENUM
        ('unreleased', 'pending-release', 'released', 'refunded');

    ALTER TABLE participants
        ADD COLUMN status_of_1_0_balance status_of_1_0_balance
        NOT NULL
        DEFAULT 'unreleased';

END;
