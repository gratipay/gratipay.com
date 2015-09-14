BEGIN;

    CREATE FUNCTION current_payday() RETURNS paydays AS $$
        SELECT *
          FROM paydays
         WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz;
    $$ LANGUAGE sql;

    CREATE FUNCTION current_payday_id() RETURNS int AS $$
        -- This is a function so we can use it in DEFAULTS for a column.
        SELECT id FROM current_payday();
    $$ LANGUAGE sql;

END;
