-- Recreate the necessary tables and indexes

DROP TABLE IF EXISTS payday_participants;
CREATE TABLE payday_participants AS
    SELECT id
         , username
         , claimed_time
         , balance AS old_balance
         , balance AS new_balance
         , is_suspicious
         , false AS card_hold_ok
         , ( SELECT count(*)
               FROM current_exchange_routes r
              WHERE r.participant = p.id
                AND network = 'braintree-cc'
                AND error = ''
           ) > 0 AS has_credit_card
          , braintree_customer_id
      FROM participants p
     WHERE is_suspicious IS NOT true
       AND claimed_time < (SELECT ts_start FROM current_payday())
  ORDER BY claimed_time;

CREATE UNIQUE INDEX ON payday_participants (id);
CREATE UNIQUE INDEX ON payday_participants (username);

DROP TABLE IF EXISTS payday_teams;
CREATE TABLE payday_teams AS
    SELECT t.id
         , slug
         , owner
         , available
         , 0::numeric(35, 2) AS balance
         , false AS is_drained
      FROM teams t
      JOIN participants p
        ON t.owner = p.username
     WHERE t.is_approved IS true
       AND t.is_closed IS NOT true
       AND p.claimed_time IS NOT null
       AND p.is_closed IS NOT true
       AND p.is_suspicious IS NOT true
       AND (SELECT count(*)
              FROM current_exchange_routes er
             WHERE er.participant = p.id
               AND network = 'paypal'
               AND error = ''
            ) > 0
    ;

DROP TABLE IF EXISTS payday_payments_done;
CREATE TABLE payday_payments_done AS
    SELECT *
      FROM payments p
     WHERE p.timestamp > (SELECT ts_start FROM current_payday());

DROP TABLE IF EXISTS payday_payment_instructions;
CREATE TABLE payday_payment_instructions AS
    SELECT s.id, participant_id, team_id, amount, due
      FROM ( SELECT DISTINCT ON (participant_id, team_id) *
               FROM payment_instructions
              WHERE mtime < (SELECT ts_start FROM current_payday())
           ORDER BY participant_id, team_id, mtime DESC
           ) s
      JOIN payday_participants p ON p.id = s.participant_id
      JOIN payday_teams t ON t.id = s.team_id
     WHERE s.amount > 0
       AND ( SELECT id
               FROM payday_payments_done done
              WHERE p.username = done.participant
                AND t.slug = done.team
                AND direction = 'to-team'
           ) IS NULL
  ORDER BY p.claimed_time ASC, s.ctime ASC;

CREATE INDEX ON payday_payment_instructions (participant_id);
CREATE INDEX ON payday_payment_instructions (team_id);
ALTER TABLE payday_payment_instructions ADD COLUMN is_funded boolean;

ALTER TABLE payday_participants ADD COLUMN giving_today numeric(35,2);
UPDATE payday_participants pp
   SET giving_today = COALESCE((
           SELECT sum(amount + due)
             FROM payday_payment_instructions
            WHERE participant_id = pp.id
       ), 0);

DROP TABLE IF EXISTS payday_takes;
CREATE TABLE payday_takes
( team_id           bigint
, participant_id    bigint
, amount            numeric(35,2)
 );

DROP TABLE IF EXISTS payday_payments;
CREATE TABLE payday_payments
( timestamp timestamptz         DEFAULT now()
, participant text              NOT NULL
, team text                     NOT NULL
, amount numeric(35,2)          NOT NULL
, direction payment_direction   NOT NULL
 );


-- Prepare a statement that makes and records a payment

CREATE OR REPLACE FUNCTION pay(bigint, bigint, numeric, payment_direction)
RETURNS void AS $$
    DECLARE
        participant_delta numeric;
        team_delta numeric;
        payload json;
    BEGIN
        IF ($3 = 0) THEN RETURN; END IF;

        IF ($4 = 'to-team') THEN
            participant_delta := -$3;
            team_delta := $3;
        ELSE
            participant_delta := $3;
            team_delta := -$3;
        END IF;

        UPDATE payday_participants
           SET new_balance = (new_balance + participant_delta)
         WHERE id = $1;
        UPDATE payday_teams
           SET balance = (balance + team_delta)
         WHERE id = $2;
        UPDATE current_payment_instructions
           SET due = 0
         WHERE participant_id = $1
           AND team_id = $2
           AND due > 0;
        IF ($4 = 'to-team') THEN
            payload = '{"action":"pay","participant_id":"' || $1 || '", "team_id":"'
                || $2 || '", "amount":' || $3 || '}';
            INSERT INTO events(type, payload)
                VALUES ('payday',payload);
        END IF;
        INSERT INTO payday_payments
                    (participant, team, amount, direction)
             VALUES ( ( SELECT p.username
                          FROM participants p
                          JOIN payday_participants p2 ON p.id = p2.id
                         WHERE p2.id = $1 )
                    , ( SELECT t.slug
                          FROM teams t
                          JOIN payday_teams t2 ON t.id = t2.id
                         WHERE t2.id = $2 )
                    , $3
                    , $4
                     );
    END;
$$ LANGUAGE plpgsql;

-- Add payments that were not met on to due

CREATE OR REPLACE FUNCTION park(bigint, bigint, numeric)
RETURNS void AS $$
    DECLARE payload json;
    BEGIN
        IF ($3 = 0) THEN RETURN; END IF;

        UPDATE current_payment_instructions
           SET due = $3
         WHERE participant_id = $1
           AND team_id = $2;

        payload = '{"action":"due","participant_id":"' || $1 || '", "team_id":"'
            || $2 || '", "due":' || $3 || '}';
        INSERT INTO events(type, payload)
            VALUES ('payday',payload);

    END;
$$ LANGUAGE plpgsql;


-- Create a trigger to process payment_instructions

CREATE OR REPLACE FUNCTION process_payment_instruction() RETURNS trigger AS $$
    DECLARE
        participant payday_participants;
    BEGIN
        participant := (
            SELECT p.*::payday_participants
              FROM payday_participants p
             WHERE id = NEW.participant_id
        );

        IF (NEW.amount + NEW.due <= participant.new_balance OR participant.card_hold_ok) THEN
            EXECUTE pay(NEW.participant_id, NEW.team_id, NEW.amount + NEW.due, 'to-team');
            RETURN NEW;
        ELSIF participant.has_credit_card THEN
            EXECUTE park(NEW.participant_id, NEW.team_id, NEW.amount + NEW.due);
            RETURN NULL;
        END IF;

        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_payment_instruction BEFORE UPDATE OF is_funded ON payday_payment_instructions
    FOR EACH ROW
    WHEN (NEW.is_funded IS true AND OLD.is_funded IS NOT true)
    EXECUTE PROCEDURE process_payment_instruction();


-- Create a trigger to process distributions based on takes

CREATE OR REPLACE FUNCTION process_distribution() RETURNS trigger AS $$
    DECLARE
        amount      numeric(35,2);
        balance_    numeric(35,2);
        available_  numeric(35,2);
    BEGIN
        amount := NEW.amount;

        balance_ := (SELECT balance FROM payday_teams WHERE id = NEW.team_id);
        IF balance_ < amount THEN
            amount := balance_;
        END IF;

        available_ := (SELECT available FROM payday_teams WHERE id = NEW.team_id);
        IF available_ < amount THEN
            amount := available_;
        END IF;

        IF amount > 0 THEN
            UPDATE payday_teams SET available = (available - amount) WHERE id = NEW.team_id;
            EXECUTE pay(NEW.participant_id, NEW.team_id, amount, 'to-participant');
        END IF;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_takes AFTER INSERT ON payday_takes
    FOR EACH ROW EXECUTE PROCEDURE process_distribution();


-- Create a trigger to process draws

CREATE OR REPLACE FUNCTION process_draw() RETURNS trigger AS $$
    BEGIN
        EXECUTE pay( (SELECT id FROM participants WHERE username=NEW.owner)
                   , NEW.id
                   , NEW.balance
                   , 'to-participant'
                    );
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_draw BEFORE UPDATE OF is_drained ON payday_teams
    FOR EACH ROW
    WHEN (NEW.is_drained IS true AND OLD.is_drained IS NOT true)
    EXECUTE PROCEDURE process_draw();
