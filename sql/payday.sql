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
       AND claimed_time < %(ts_start)s
  ORDER BY claimed_time;

CREATE UNIQUE INDEX ON payday_participants (id);
CREATE UNIQUE INDEX ON payday_participants (username);

DROP TABLE IF EXISTS payday_teams;
CREATE TABLE payday_teams AS
    SELECT t.id
         , slug
         , owner
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
     WHERE p.timestamp > %(ts_start)s;

DROP TABLE IF EXISTS payday_payment_instructions;
CREATE TABLE payday_payment_instructions AS
    SELECT s.id, participant, team, amount, giving_due
      FROM ( SELECT DISTINCT ON (participant, team) *
               FROM payment_instructions
              WHERE mtime < %(ts_start)s
           ORDER BY participant, team, mtime DESC
           ) s
      JOIN payday_participants p ON p.username = s.participant
      JOIN payday_teams t ON t.slug = s.team
     WHERE s.amount > 0
       AND ( SELECT id
               FROM payday_payments_done done
              WHERE s.participant = done.participant
                AND s.team = done.team
                AND direction = 'to-team'
           ) IS NULL
  ORDER BY p.claimed_time ASC, s.ctime ASC;

CREATE INDEX ON payday_payment_instructions (participant);
CREATE INDEX ON payday_payment_instructions (team);
ALTER TABLE payday_payment_instructions ADD COLUMN is_funded boolean;

UPDATE payday_payment_instructions ppi
   SET giving_due = s.giving_due
  FROM (SELECT participant, team, SUM(giving_due) AS giving_due
       FROM payment_instructions
       GROUP BY participant, team) s
 WHERE ppi.participant = s.participant
   AND ppi.team = s.team;

DROP TABLE IF EXISTS participants_payments_uncharged;
CREATE TABLE participants_payments_uncharged AS
    SELECT id, giving_due
      FROM payday_payment_instructions
     WHERE 1 = 2;

ALTER TABLE payday_participants ADD COLUMN giving_today numeric(35,2);
UPDATE payday_participants pp
   SET giving_today = COALESCE((
           SELECT sum(amount + giving_due)
             FROM payday_payment_instructions
            WHERE participant = pp.username
       ), 0);

DROP TABLE IF EXISTS payday_takes;
CREATE TABLE payday_takes
( team text
, member text
, amount numeric(35,2)
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

CREATE OR REPLACE FUNCTION pay(text, text, numeric, payment_direction)
RETURNS void AS $$
    DECLARE
        participant_delta numeric;
        team_delta numeric;
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
         WHERE username = $1;
        UPDATE payday_teams
           SET balance = (balance + team_delta)
         WHERE slug = $2;
        UPDATE payday_payment_instructions
           SET giving_due = 0
         WHERE participant = $1
           AND team = $2
           AND giving_due > 0;
        INSERT INTO payday_payments
                    (participant, team, amount, direction)
             VALUES ( ( SELECT p.username
                          FROM participants p
                          JOIN payday_participants p2 ON p.id = p2.id
                         WHERE p2.username = $1 )
                    , ( SELECT t.slug
                          FROM teams t
                          JOIN payday_teams t2 ON t.id = t2.id
                         WHERE t2.slug = $2 )
                    , $3
                    , $4
                     );
    END;
$$ LANGUAGE plpgsql;

-- Add payments that were not met on to giving_due

CREATE OR REPLACE FUNCTION park(text, text, numeric)
RETURNS void AS $$
    BEGIN
        IF ($3 = 0) THEN RETURN; END IF;

        UPDATE payday_payment_instructions
           SET giving_due = $3
         WHERE participant = $1
           AND team = $2;
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
             WHERE username = NEW.participant
        );
        IF (NEW.amount + NEW.giving_due <= participant.new_balance OR participant.card_hold_ok) THEN
            EXECUTE pay(NEW.participant, NEW.team, NEW.amount + NEW.giving_due, 'to-team');
            RETURN NEW;
        ELSE
            EXECUTE park(NEW.participant, NEW.team, NEW.amount + NEW.giving_due);
            RETURN NULL;
        END IF;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_payment_instruction BEFORE UPDATE OF is_funded ON payday_payment_instructions
    FOR EACH ROW
    WHEN (NEW.is_funded IS true AND OLD.is_funded IS NOT true)
    EXECUTE PROCEDURE process_payment_instruction();


-- Create a trigger to process takes

CREATE OR REPLACE FUNCTION process_take() RETURNS trigger AS $$
    DECLARE
        actual_amount numeric(35,2);
        team_balance numeric(35,2);
    BEGIN
        team_balance := (
            SELECT new_balance
              FROM payday_participants
             WHERE username = NEW.team
        );
        IF (team_balance <= 0) THEN RETURN NULL; END IF;
        actual_amount := NEW.amount;
        IF (team_balance < NEW.amount) THEN
            actual_amount := team_balance;
        END IF;
        EXECUTE transfer(NEW.team, NEW.member, actual_amount, 'take');
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_take AFTER INSERT ON payday_takes
    FOR EACH ROW EXECUTE PROCEDURE process_take();


-- Create a trigger to process draws

CREATE OR REPLACE FUNCTION process_draw() RETURNS trigger AS $$
    BEGIN
        EXECUTE pay(NEW.owner, NEW.slug, NEW.balance, 'to-participant');
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_draw BEFORE UPDATE OF is_drained ON payday_teams
    FOR EACH ROW
    WHEN (NEW.is_drained IS true AND OLD.is_drained IS NOT true)
    EXECUTE PROCEDURE process_draw();
