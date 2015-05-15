-- Create the necessary temporary tables and indexes

CREATE TEMPORARY TABLE payday_participants ON COMMIT DROP AS
    SELECT id
         , username
         , claimed_time
         , balance AS old_balance
         , balance AS new_balance
         , is_suspicious
         , false AS card_hold_ok
         , ( SELECT count(*)
               FROM exchange_routes r
              WHERE r.participant = p.id
                AND network = 'balanced-cc'
           ) > 0 AS has_credit_card
      FROM participants p
     WHERE is_suspicious IS NOT true
       AND claimed_time < %(ts_start)s
  ORDER BY claimed_time;

CREATE UNIQUE INDEX ON payday_participants (id);
CREATE UNIQUE INDEX ON payday_participants (username);

CREATE TEMPORARY TABLE payday_teams ON COMMIT DROP AS
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
              FROM exchange_routes er
             WHERE er.participant = p.id
               AND network IN ('balanced-ba', 'paypal')
               AND error = ''
            ) > 0
    ;

CREATE TEMPORARY TABLE payday_payments_done ON COMMIT DROP AS
    SELECT *
      FROM payments p
     WHERE p.timestamp > %(ts_start)s;

CREATE TEMPORARY TABLE payday_subscriptions ON COMMIT DROP AS
    SELECT subscriber, team, amount
      FROM ( SELECT DISTINCT ON (subscriber, team) *
               FROM subscriptions
              WHERE mtime < %(ts_start)s
           ORDER BY subscriber, team, mtime DESC
           ) s
      JOIN payday_participants p ON p.username = s.subscriber
      JOIN payday_teams t ON t.slug = s.team
     WHERE s.amount > 0
       AND ( SELECT id
               FROM payday_payments_done done
              WHERE s.subscriber = done.participant
                AND s.team = done.team
                AND direction = 'to-team'
           ) IS NULL
  ORDER BY p.claimed_time ASC, s.ctime ASC;

CREATE INDEX ON payday_subscriptions (subscriber);
CREATE INDEX ON payday_subscriptions (team);
ALTER TABLE payday_subscriptions ADD COLUMN is_funded boolean;

ALTER TABLE payday_participants ADD COLUMN giving_today numeric(35,2);
UPDATE payday_participants
   SET giving_today = COALESCE((
           SELECT sum(amount)
             FROM payday_subscriptions
            WHERE subscriber = username
       ), 0);

CREATE TEMPORARY TABLE payday_takes
( team text
, member text
, amount numeric(35,2)
 ) ON COMMIT DROP;

CREATE TEMPORARY TABLE payday_payments
( timestamp timestamptz         DEFAULT now()
, participant text              NOT NULL
, team text                     NOT NULL
, amount numeric(35,2)          NOT NULL
, direction payment_direction   NOT NULL
 ) ON COMMIT DROP;


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


-- Create a trigger to process subscriptions

CREATE OR REPLACE FUNCTION process_subscription() RETURNS trigger AS $$
    DECLARE
        subscriber payday_participants;
    BEGIN
        subscriber := (
            SELECT p.*::payday_participants
              FROM payday_participants p
             WHERE username = NEW.subscriber
        );
        IF (NEW.amount <= subscriber.new_balance OR subscriber.card_hold_ok) THEN
            EXECUTE pay(NEW.subscriber, NEW.team, NEW.amount, 'to-team');
            RETURN NEW;
        END IF;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_subscription BEFORE UPDATE OF is_funded ON payday_subscriptions
    FOR EACH ROW
    WHEN (NEW.is_funded IS true AND OLD.is_funded IS NOT true)
    EXECUTE PROCEDURE process_subscription();


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


-- Save the stats we already have

UPDATE paydays
   SET nparticipants = (SELECT count(*) FROM payday_participants)
     , ncc_missing = (
           SELECT count(*)
             FROM payday_participants
            WHERE old_balance < giving_today
              AND NOT has_credit_card
       )
 WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz;
