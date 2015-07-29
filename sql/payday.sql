-- Participants

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

CREATE OR REPLACE FUNCTION protect_balances() RETURNS trigger AS $$
BEGIN
    IF NEW.new_balance < LEAST(0, OLD.new_balance) THEN
        RAISE 'You''re trying to make balance more negative for %.', NEW.username
            USING ERRCODE = '23000';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER protect_balances AFTER UPDATE ON payday_participants
    FOR EACH ROW EXECUTE PROCEDURE protect_balances();


-- Teams

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

CREATE OR REPLACE FUNCTION protect_team_balances() RETURNS trigger AS $$
BEGIN
    IF NEW.balance < 0 THEN
        RAISE 'You''re trying to set a negative balance for the % team.', NEW.slug
            USING ERRCODE = '23000';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER protect_team_balances AFTER UPDATE ON payday_teams
    FOR EACH ROW EXECUTE PROCEDURE protect_team_balances();


-- Subscriptions

DROP TABLE IF EXISTS payday_journal_so_far;
CREATE TABLE payday_journal_so_far AS
    SELECT * FROM journal WHERE payday = (SELECT id FROM current_payday());

DROP TABLE IF EXISTS payday_subscriptions;
CREATE TABLE payday_subscriptions AS
    SELECT subscriber, team, amount
      FROM ( SELECT DISTINCT ON (subscriber, team) *
               FROM subscriptions
              WHERE mtime < (SELECT ts_start FROM current_payday())
           ORDER BY subscriber, team, mtime DESC
           ) s
      JOIN payday_participants p ON p.username = s.subscriber
     WHERE s.amount > 0
       AND ( SELECT id
               FROM payday_journal_so_far so_far
              WHERE so_far.debit = (SELECT id FROM accounts WHERE team=s.team)
                AND so_far.credit = (SELECT id FROM accounts WHERE participant=s.subscriber)
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


-- Takes

DROP TABLE IF EXISTS payday_takes;
CREATE TABLE payday_takes
( team text
, member text
, amount numeric(35,2)
 );


-- Journal

DROP TABLE IF EXISTS payday_journal;
CREATE TABLE payday_journal
( ts timestamptz        DEFAULT now()
, amount numeric(35,2)  NOT NULL
, debit bigint          NOT NULL
, credit bigint         NOT NULL
, payday int            NOT NULL DEFAULT current_payday_id()
 );

CREATE OR REPLACE FUNCTION payday_update_balance() RETURNS trigger AS $$
DECLARE
    to_debit            text;
    to_credit           text;
BEGIN
    to_debit = (SELECT participant FROM accounts WHERE id=NEW.debit);
    IF to_debit IS NOT NULL THEN

        -- Fulfillment of a subscription from a ~user to a Team.

        to_credit = (SELECT team FROM accounts WHERE id=NEW.credit);

        UPDATE payday_participants
           SET new_balance = new_balance - NEW.amount
         WHERE username = to_debit;

        UPDATE payday_teams
           SET balance = balance + NEW.amount
         WHERE slug = to_credit;

    ELSE

        -- Payroll from a Team to a ~user.

        to_debit = (SELECT team FROM accounts WHERE id=NEW.debit);
        to_credit = (SELECT participant FROM accounts WHERE id=NEW.credit);

        UPDATE payday_teams
           SET balance = balance - NEW.amount
         WHERE slug = to_debit;

        UPDATE payday_participants
           SET new_balance = new_balance + NEW.amount
         WHERE username = to_credit;

    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payday_update_balance AFTER INSERT ON payday_journal
    FOR EACH ROW EXECUTE PROCEDURE payday_update_balance();


-- Prepare a statement that makes a journal entry

CREATE OR REPLACE FUNCTION pay(text, text, numeric, payment_direction)
RETURNS void AS $$
    DECLARE
        participant_account bigint;
        team_account        bigint;
        to_debit            bigint;
        to_credit           bigint;
    BEGIN
        IF ($3 = 0) THEN RETURN; END IF;

        participant_account := (SELECT id FROM accounts WHERE participant=$1);
        team_account := (SELECT id FROM accounts WHERE team=$2);

        IF participant_account IS NULL THEN
            RAISE 'Unknown participant: %.', $1;
        END IF;
        IF team_account IS NULL THEN
            RAISE 'Unknown team: %', $2;
        END IF;

        IF ($4 = 'to-team') THEN
            to_debit := participant_account;
            to_credit := team_account;
        ELSE
            to_debit := team_account;
            to_credit := participant_account;
        END IF;

        INSERT INTO payday_journal
                    (amount, debit, credit)
             VALUES ($3, to_debit, to_credit);
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
