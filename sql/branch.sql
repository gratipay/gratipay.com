BEGIN;
    ALTER TYPE payment_net ADD VALUE 'cash';
    ALTER TYPE payment_net ADD VALUE 'transferwise';
END;
