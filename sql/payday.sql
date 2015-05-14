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

CREATE TEMPORARY TABLE payday_transfers_done ON COMMIT DROP AS
    SELECT *
      FROM transfers t
     WHERE t.timestamp > %(ts_start)s;

CREATE TEMPORARY TABLE payday_tips ON COMMIT DROP AS
    SELECT tipper, tippee, amount
      FROM ( SELECT DISTINCT ON (tipper, tippee) *
               FROM tips
              WHERE mtime < %(ts_start)s
           ORDER BY tipper, tippee, mtime DESC
           ) t
      JOIN payday_participants p ON p.username = t.tipper
      JOIN payday_participants p2 ON p2.username = t.tippee
     WHERE t.amount > 0
       AND ( SELECT id
               FROM payday_transfers_done t2
              WHERE t.tipper = t2.tipper
                AND t.tippee = t2.tippee
                AND context = 'tip'
           ) IS NULL
  ORDER BY p.claimed_time ASC, t.ctime ASC;

CREATE INDEX ON payday_tips (tipper);
CREATE INDEX ON payday_tips (tippee);
ALTER TABLE payday_tips ADD COLUMN is_funded boolean;

ALTER TABLE payday_participants ADD COLUMN giving_today numeric(35,2);
UPDATE payday_participants
   SET giving_today = COALESCE((
           SELECT sum(amount)
             FROM payday_tips
            WHERE tipper = username
       ), 0);

CREATE TEMPORARY TABLE payday_takes
( team text
, member text
, amount numeric(35,2)
) ON COMMIT DROP;

CREATE TEMPORARY TABLE payday_transfers
( timestamp timestamptz DEFAULT now()
, tipper text
, tippee text
, amount numeric(35,2)
, context context_type
) ON COMMIT DROP;


-- Prepare a statement that makes and records a transfer

CREATE OR REPLACE FUNCTION transfer(text, text, numeric, context_type)
RETURNS void AS $$
    BEGIN
        IF ($3 = 0) THEN RETURN; END IF;
        UPDATE payday_participants
           SET new_balance = (new_balance - $3)
         WHERE username = $1;
        UPDATE payday_participants
           SET new_balance = (new_balance + $3)
         WHERE username = $2;
        INSERT INTO payday_transfers
                    (tipper, tippee, amount, context)
             VALUES ( ( SELECT p.username
                          FROM participants p
                          JOIN payday_participants p2 ON p.id = p2.id
                         WHERE p2.username = $1 )
                    , ( SELECT p.username
                          FROM participants p
                          JOIN payday_participants p2 ON p.id = p2.id
                         WHERE p2.username = $2 )
                    , $3
                    , $4
                    );
    END;
$$ LANGUAGE plpgsql;


-- Create a trigger to process tips

CREATE OR REPLACE FUNCTION process_tip() RETURNS trigger AS $$
    DECLARE
        tipper payday_participants;
    BEGIN
        tipper := (
            SELECT p.*::payday_participants
              FROM payday_participants p
             WHERE username = NEW.tipper
        );
        IF (NEW.amount <= tipper.new_balance OR tipper.card_hold_ok) THEN
            EXECUTE transfer(NEW.tipper, NEW.tippee, NEW.amount, 'tip');
            RETURN NEW;
        END IF;
        RETURN NULL;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_tip BEFORE UPDATE OF is_funded ON payday_tips
    FOR EACH ROW
    WHEN (NEW.is_funded IS true AND OLD.is_funded IS NOT true)
    EXECUTE PROCEDURE process_tip();


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


-- Create a function to settle whole tip graph

CREATE OR REPLACE FUNCTION settle_tip_graph() RETURNS void AS $$
    BEGIN
         UPDATE payday_tips
            SET is_funded = true
          WHERE is_funded IS NOT true;
    END;
$$ LANGUAGE plpgsql;


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
