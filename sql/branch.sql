BEGIN;
    ALTER TABLE exchange_routes ADD COLUMN is_deleted bool NOT NULL DEFAULT FALSE;

    DROP CAST (current_exchange_routes AS exchange_routes);
    DROP VIEW current_exchange_routes;

    CREATE VIEW current_exchange_routes AS
        SELECT DISTINCT ON (participant, network) *
          FROM exchange_routes
         WHERE NOT is_deleted
      ORDER BY participant, network, id DESC;

    CREATE CAST (current_exchange_routes AS exchange_routes) WITH INOUT;

    UPDATE exchange_routes SET is_deleted = true, error = '' WHERE error = 'invalidated';
END;