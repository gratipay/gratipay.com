-- Alter the enums to cater for missing data.
ALTER TYPE payment_net ADD VALUE 'unknown';
ALTER TYPE exchange_status ADD VALUE 'unknown';

-- Update the field status in the exchanges table from NULL to 'unknown'
UPDATE exchanges SET status = 'unknown' WHERE status IS NULL;

-- Alter the exchanges table to ensure that no more NULL values are entered
ALTER TABLE exchanges ALTER COLUMN status SET NOT NULL;

-- Insert records for ‘unknown’ (previously NULL in exchanges table
-- network in exchange_route table
INSERT INTO  exchange_routes (participant, network, address, error)
     (
       SELECT DISTINCT participants.id, 'unknown'::payment_net, 'None', 'None'
       FROM exchanges, participants
       WHERE exchanges.participant = participants.username
       AND route IS NULL
     );

-- Update exchanges records with exchange_route ids pointing to ‘unknown’ network records for that participants
UPDATE exchanges
SET route = exchange_routes.id
FROM exchange_routes, participants
WHERE exchange_routes.participant = participants.id
AND participants.username = exchanges.participant;

-- Alter exchanges table and set route to not null
ALTER TABLE exchanges ALTER COLUMN route SET NOT NULL;
