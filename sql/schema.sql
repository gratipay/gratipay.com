--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.2
-- Dumped by pg_dump version 9.6.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track execution statistics of all SQL statements executed';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET search_path = public, pg_catalog;

--
-- Name: context_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE context_type AS ENUM (
    'tip',
    'take',
    'final-gift',
    'take-over',
    'one-off'
);


--
-- Name: status_of_1_0_payout; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE status_of_1_0_payout AS ENUM (
    'too-little',
    'pending-application',
    'pending-review',
    'rejected',
    'pending-payout',
    'completed'
);


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE participants (
    username text NOT NULL,
    session_token text,
    session_expires timestamp with time zone DEFAULT (now() + '06:00:00'::interval),
    ctime timestamp with time zone DEFAULT now() NOT NULL,
    claimed_time timestamp with time zone,
    is_admin boolean DEFAULT false NOT NULL,
    balance numeric(35,2) DEFAULT 0.0 NOT NULL,
    anonymous_giving boolean DEFAULT false NOT NULL,
    balanced_customer_href text,
    is_suspicious boolean,
    id bigint NOT NULL,
    username_lower text NOT NULL,
    api_key text,
    avatar_url text,
    is_closed boolean DEFAULT false NOT NULL,
    giving numeric(35,2) DEFAULT 0 NOT NULL,
    taking numeric(35,2) DEFAULT 0 NOT NULL,
    is_free_rider boolean,
    email_address text,
    email_lang text,
    is_searchable boolean DEFAULT true NOT NULL,
    old_auth_usage date,
    notifications text[] DEFAULT '{}'::text[] NOT NULL,
    notify_charge integer DEFAULT 3,
    braintree_customer_id text,
    ngiving_to integer DEFAULT 0 NOT NULL,
    ntaking_from integer DEFAULT 0 NOT NULL,
    status_of_1_0_payout status_of_1_0_payout DEFAULT 'completed'::status_of_1_0_payout NOT NULL,
    has_verified_identity boolean DEFAULT false NOT NULL,
    is_owner boolean DEFAULT false NOT NULL
);


--
-- Name: elsewhere_with_participant; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE elsewhere_with_participant AS (
	id integer,
	platform text,
	user_id text,
	user_name text,
	display_name text,
	email text,
	avatar_url text,
	is_team boolean,
	extra_info json,
	token json,
	connect_token text,
	connect_expires timestamp with time zone,
	participant participants
);


--
-- Name: exchange_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE exchange_status AS ENUM (
    'pre',
    'pending',
    'failed',
    'succeeded',
    'unknown'
);


--
-- Name: follow_up; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE follow_up AS ENUM (
    'monthly',
    'quarterly',
    'yearly',
    'never'
);


--
-- Name: participant_number; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE participant_number AS ENUM (
    'singular',
    'plural'
);


--
-- Name: payment_direction; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE payment_direction AS ENUM (
    'to-team',
    'to-participant'
);


--
-- Name: payment_net; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE payment_net AS ENUM (
    'balanced-ba',
    'balanced-cc',
    'paypal',
    'bitcoin',
    'braintree-cc',
    'cash',
    'transferwise',
    'dwolla',
    'unknown'
);


--
-- Name: status_of_1_0_balance; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE status_of_1_0_balance AS ENUM (
    'unresolved',
    'pending-payout',
    'resolved'
);


--
-- Name: supported_image_types; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE supported_image_types AS ENUM (
    'image/png',
    'image/jpeg'
);


--
-- Name: complete_1_0_payout(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION complete_1_0_payout() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            UPDATE participants
               SET status_of_1_0_payout='completed'
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$;


--
-- Name: paydays; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE paydays (
    id integer NOT NULL,
    ts_start timestamp with time zone DEFAULT now() NOT NULL,
    ts_end timestamp with time zone DEFAULT '1970-01-01 00:00:00+00'::timestamp with time zone NOT NULL,
    volume numeric(35,2) DEFAULT 0.00 NOT NULL,
    nusers bigint DEFAULT 0 NOT NULL,
    stage integer DEFAULT 0,
    nteams integer DEFAULT 0 NOT NULL
);


--
-- Name: current_payday(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION current_payday() RETURNS paydays
    LANGUAGE sql
    AS $$
        SELECT *
          FROM paydays
         WHERE ts_end='1970-01-01T00:00:00+00'::timestamptz;
    $$;


--
-- Name: current_payday_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION current_payday_id() RETURNS integer
    LANGUAGE sql
    AS $$
        -- This is a function so we can use it in DEFAULTS for a column.
        SELECT id FROM current_payday();
    $$;


--
-- Name: enumerate(anyarray); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION enumerate(anyarray) RETURNS TABLE(rank bigint, value anyelement)
    LANGUAGE sql STABLE
    AS $_$
    SELECT row_number() over() as rank, value FROM unnest($1) value;
$_$;


--
-- Name: fail_if_no_email(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fail_if_no_email() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF (SELECT email_address FROM participants WHERE id=NEW.participant_id) IS NULL THEN
            RAISE EXCEPTION
            USING ERRCODE=23100
                , MESSAGE='This operation requires a verified participant email address.';
        END IF;
        RETURN NEW;
    END;
$$;


--
-- Name: elsewhere; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE elsewhere (
    id integer NOT NULL,
    platform text NOT NULL,
    user_id text NOT NULL,
    participant text NOT NULL,
    user_name text,
    display_name text,
    email text,
    avatar_url text,
    is_team boolean DEFAULT false NOT NULL,
    extra_info json,
    token json,
    connect_token text,
    connect_expires timestamp with time zone
);


--
-- Name: load_participant_for_elsewhere(elsewhere); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION load_participant_for_elsewhere(elsewhere) RETURNS elsewhere_with_participant
    LANGUAGE sql
    AS $_$
    SELECT $1.id
         , $1.platform
         , $1.user_id
         , $1.user_name
         , $1.display_name
         , $1.email
         , $1.avatar_url
         , $1.is_team
         , $1.extra_info
         , $1.token
         , $1.connect_token
         , $1.connect_expires
         , participants.*::participants
      FROM participants
     WHERE participants.username = $1.participant;
$_$;


--
-- Name: park(bigint, bigint, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION park(bigint, bigint, numeric) RETURNS void
    LANGUAGE plpgsql
    AS $_$
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
$_$;


--
-- Name: pay(bigint, bigint, numeric, payment_direction); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION pay(bigint, bigint, numeric, payment_direction) RETURNS void
    LANGUAGE plpgsql
    AS $_$
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
$_$;


--
-- Name: process_draw(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION process_draw() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        EXECUTE pay( (SELECT id FROM participants WHERE username=NEW.owner)
                   , NEW.id
                   , NEW.balance
                   , 'to-participant'
                    );
        RETURN NULL;
    END;
$$;


--
-- Name: process_payment_instruction(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION process_payment_instruction() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: process_take(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION process_take() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        amount              numeric(35,2);
        available_today_    numeric(35,2);
    BEGIN
        amount := NEW.amount;
        available_today_ := (SELECT available_today FROM payday_teams WHERE id = NEW.team_id);

        IF amount > available_today_ THEN
            amount := available_today_;
        END IF;

        IF amount > 0 THEN
            UPDATE payday_teams
               SET available_today = (available_today - amount)
             WHERE id = NEW.team_id;
            EXECUTE pay(NEW.participant_id, NEW.team_id, amount, 'to-participant');
        END IF;
        RETURN NULL;
    END;
$$;


--
-- Name: update_payment_instruction(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION update_payment_instruction() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            UPDATE payment_instructions
               SET is_funded = NEW.is_funded
                 , due = NEW.due
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$;


--
-- Name: update_tip(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION update_tip() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            UPDATE tips
               SET is_funded = NEW.is_funded
             WHERE id = NEW.id;
            RETURN NULL;
        END;
    $$;


--
-- Name: upsert_community(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION upsert_community() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        is_member boolean;
        delta int = CASE WHEN NEW.is_member THEN 1 ELSE -1 END;
    BEGIN
        IF (SELECT is_suspicious FROM participants WHERE id = NEW.participant) THEN
            RETURN NULL;
        END IF;
        is_member := (
            SELECT cur.is_member
              FROM community_members cur
             WHERE slug = NEW.slug
               AND participant = NEW.participant
          ORDER BY mtime DESC
             LIMIT 1
        );
        IF (is_member IS NULL AND NEW.is_member IS false OR NEW.is_member = is_member) THEN
            RETURN NULL;
        END IF;
        LOOP
            UPDATE communities
               SET nmembers = nmembers + delta
             WHERE slug = NEW.slug
               AND nmembers + delta > 0;
            EXIT WHEN FOUND;
            IF (NEW.is_member) THEN
                BEGIN
                    INSERT INTO communities
                         VALUES (NEW.slug, NEW.name, 1, NEW.ctime);
                EXCEPTION
                    WHEN unique_violation THEN
                        IF (CONSTRAINT_NAME = 'communities_slug_pkey') THEN
                            CONTINUE; -- Try again
                        ELSE
                            RAISE;
                        END IF;
                END;
                EXIT;
            ELSE
                DELETE FROM communities WHERE slug = NEW.slug AND nmembers = 1;
                EXIT WHEN FOUND;
            END IF;
        END LOOP;
        RETURN NEW;
    END;
$$;


--
-- Name: exchange_routes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE exchange_routes (
    id integer NOT NULL,
    participant bigint NOT NULL,
    network payment_net NOT NULL,
    address text NOT NULL,
    error text NOT NULL,
    fee_cap numeric(35,2),
    is_deleted boolean DEFAULT false NOT NULL,
    CONSTRAINT exchange_routes_address_check CHECK ((address <> ''::text))
);


--
-- Name: current_exchange_routes; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW current_exchange_routes AS
 SELECT DISTINCT ON (exchange_routes.participant, exchange_routes.network) exchange_routes.id,
    exchange_routes.participant,
    exchange_routes.network,
    exchange_routes.address,
    exchange_routes.error,
    exchange_routes.fee_cap,
    exchange_routes.is_deleted
   FROM exchange_routes
  WHERE (NOT exchange_routes.is_deleted)
  ORDER BY exchange_routes.participant, exchange_routes.network, exchange_routes.id DESC;


SET search_path = pg_catalog;

--
-- Name: CAST (public.current_exchange_routes AS public.exchange_routes); Type: CAST; Schema: pg_catalog; Owner: -
--

CREATE CAST (public.current_exchange_routes AS public.exchange_routes) WITH INOUT;


--
-- Name: CAST (public.elsewhere AS public.elsewhere_with_participant); Type: CAST; Schema: pg_catalog; Owner: -
--

CREATE CAST (public.elsewhere AS public.elsewhere_with_participant) WITH FUNCTION public.load_participant_for_elsewhere(public.elsewhere);


SET search_path = public, pg_catalog;

--
-- Name: absorptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE absorptions (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    absorbed_was text NOT NULL,
    absorbed_by text NOT NULL,
    archived_as text NOT NULL
);


--
-- Name: absorptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE absorptions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: absorptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE absorptions_id_seq OWNED BY absorptions.id;


--
-- Name: balances_at; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE balances_at (
    participant bigint NOT NULL,
    at timestamp with time zone NOT NULL,
    balance numeric(35,2) NOT NULL
);


--
-- Name: claims; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE claims (
    nonce text NOT NULL,
    package_id bigint NOT NULL
);


--
-- Name: communities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE communities (
    slug text NOT NULL,
    name text NOT NULL,
    nmembers integer NOT NULL,
    ctime timestamp with time zone NOT NULL,
    CONSTRAINT communities_nmembers_check CHECK ((nmembers > 0))
);


--
-- Name: community_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE community_members (
    slug text NOT NULL,
    participant bigint NOT NULL,
    ctime timestamp with time zone NOT NULL,
    mtime timestamp with time zone DEFAULT now() NOT NULL,
    name text NOT NULL,
    is_member boolean NOT NULL
);


--
-- Name: countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE countries (
    id bigint NOT NULL,
    code text NOT NULL
);


--
-- Name: countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE countries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE countries_id_seq OWNED BY countries.id;


--
-- Name: current_community_members; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW current_community_members AS
 SELECT DISTINCT ON (c.participant, c.slug) c.slug,
    c.participant,
    c.ctime,
    c.mtime,
    c.name,
    c.is_member
   FROM community_members c
  ORDER BY c.participant, c.slug, c.mtime DESC;


--
-- Name: payment_instructions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payment_instructions (
    id integer NOT NULL,
    ctime timestamp with time zone NOT NULL,
    mtime timestamp with time zone DEFAULT now() NOT NULL,
    amount numeric(35,2) NOT NULL,
    is_funded boolean DEFAULT false NOT NULL,
    due numeric(35,2) DEFAULT 0,
    participant_id bigint NOT NULL,
    team_id bigint NOT NULL
);


--
-- Name: current_payment_instructions; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW current_payment_instructions AS
 SELECT DISTINCT ON (payment_instructions.participant_id, payment_instructions.team_id) payment_instructions.id,
    payment_instructions.ctime,
    payment_instructions.mtime,
    payment_instructions.amount,
    payment_instructions.is_funded,
    payment_instructions.due,
    payment_instructions.participant_id,
    payment_instructions.team_id
   FROM payment_instructions
  ORDER BY payment_instructions.participant_id, payment_instructions.team_id, payment_instructions.mtime DESC;


--
-- Name: takes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE takes (
    id bigint NOT NULL,
    ctime timestamp with time zone NOT NULL,
    mtime timestamp with time zone DEFAULT now() NOT NULL,
    participant_id bigint NOT NULL,
    team_id bigint NOT NULL,
    amount numeric(35,2) NOT NULL,
    recorder_id bigint NOT NULL,
    CONSTRAINT not_negative CHECK ((amount >= (0)::numeric))
);


--
-- Name: current_takes; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW current_takes AS
 SELECT anon.id,
    anon.ctime,
    anon.mtime,
    anon.participant_id,
    anon.team_id,
    anon.amount,
    anon.recorder_id
   FROM ( SELECT DISTINCT ON (t.participant_id, t.team_id) t.id,
            t.ctime,
            t.mtime,
            t.participant_id,
            t.team_id,
            t.amount,
            t.recorder_id
           FROM (takes t
             JOIN participants p ON ((p.id = t.participant_id)))
          WHERE (p.is_suspicious IS NOT TRUE)
          ORDER BY t.participant_id, t.team_id, t.mtime DESC) anon
  WHERE (anon.amount > (0)::numeric);


--
-- Name: tips; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE tips (
    id integer NOT NULL,
    ctime timestamp with time zone NOT NULL,
    mtime timestamp with time zone DEFAULT now() NOT NULL,
    tipper text NOT NULL,
    tippee text NOT NULL,
    amount numeric(35,2) NOT NULL,
    is_funded boolean DEFAULT false NOT NULL
);


--
-- Name: current_tips; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW current_tips AS
 SELECT DISTINCT ON (tips.tipper, tips.tippee) tips.id,
    tips.ctime,
    tips.mtime,
    tips.tipper,
    tips.tippee,
    tips.amount,
    tips.is_funded
   FROM tips
  ORDER BY tips.tipper, tips.tippee, tips.mtime DESC;


--
-- Name: elsewhere_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE elsewhere_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elsewhere_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE elsewhere_id_seq OWNED BY elsewhere.id;


--
-- Name: email_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_addresses (
    id integer NOT NULL,
    address text NOT NULL,
    verified boolean,
    nonce text,
    verification_start timestamp with time zone DEFAULT now() NOT NULL,
    verification_end timestamp with time zone,
    participant_id bigint NOT NULL,
    CONSTRAINT verified_cant_be_false CHECK ((verified IS NOT FALSE))
);


--
-- Name: email_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_messages (
    id integer NOT NULL,
    participant bigint,
    spt_name text NOT NULL,
    context bytea NOT NULL,
    user_initiated boolean DEFAULT true NOT NULL,
    ctime timestamp with time zone DEFAULT now() NOT NULL,
    result text,
    remote_message_id text,
    email_address text,
    CONSTRAINT email_or_participant_required CHECK (((participant IS NOT NULL) OR (email_address IS NOT NULL)))
);


--
-- Name: email_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE email_queue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE email_queue_id_seq OWNED BY email_messages.id;


--
-- Name: emails_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE emails_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: emails_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE emails_id_seq OWNED BY email_addresses.id;


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE events (
    id integer NOT NULL,
    ts timestamp without time zone DEFAULT now() NOT NULL,
    type text NOT NULL,
    payload json
);


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE events_id_seq OWNED BY events.id;


--
-- Name: exchange_routes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE exchange_routes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exchange_routes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE exchange_routes_id_seq OWNED BY exchange_routes.id;


--
-- Name: exchanges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE exchanges (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    amount numeric(35,2) NOT NULL,
    fee numeric(35,2) NOT NULL,
    participant text NOT NULL,
    recorder text,
    note text,
    status exchange_status NOT NULL,
    route bigint NOT NULL,
    ref text
);


--
-- Name: exchanges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE exchanges_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exchanges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE exchanges_id_seq OWNED BY exchanges.id;


--
-- Name: packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE packages (
    id bigint NOT NULL,
    package_manager text NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    emails text[] NOT NULL
);


--
-- Name: packages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE packages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: packages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE packages_id_seq OWNED BY packages.id;


--
-- Name: participant_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE participant_identities (
    id bigint NOT NULL,
    participant_id bigint NOT NULL,
    country_id bigint NOT NULL,
    schema_name text NOT NULL,
    info bytea NOT NULL,
    _info_last_keyed timestamp with time zone DEFAULT now() NOT NULL,
    is_verified boolean DEFAULT false NOT NULL
);


--
-- Name: participant_identities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE participant_identities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: participant_identities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE participant_identities_id_seq OWNED BY participant_identities.id;


--
-- Name: participants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE participants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE participants_id_seq OWNED BY participants.id;


--
-- Name: payday_participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_participants (
    id bigint,
    username text,
    claimed_time timestamp with time zone,
    old_balance numeric(35,2),
    new_balance numeric(35,2),
    is_suspicious boolean,
    card_hold_ok boolean,
    has_credit_card boolean,
    braintree_customer_id text,
    giving_today numeric(35,2)
);


--
-- Name: payday_payment_instructions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_payment_instructions (
    id integer,
    participant_id bigint,
    team_id bigint,
    amount numeric(35,2),
    due numeric(35,2),
    is_funded boolean
);


--
-- Name: payday_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_payments (
    "timestamp" timestamp with time zone DEFAULT now(),
    participant text NOT NULL,
    team text NOT NULL,
    amount numeric(35,2) NOT NULL,
    direction payment_direction NOT NULL
);


--
-- Name: payday_payments_done; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_payments_done (
    id bigint,
    "timestamp" timestamp with time zone,
    participant text,
    team text,
    amount numeric(35,2),
    direction payment_direction,
    payday integer
);


--
-- Name: payday_takes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_takes (
    team_id bigint,
    participant_id bigint,
    amount numeric(35,2)
);


--
-- Name: payday_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payday_teams (
    id bigint,
    slug text,
    owner text,
    available numeric(35,2),
    balance numeric(35,2),
    available_today numeric(35,2),
    is_drained boolean
);


--
-- Name: paydays_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE paydays_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: paydays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE paydays_id_seq OWNED BY paydays.id;


--
-- Name: payment_instructions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payment_instructions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_instructions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payment_instructions_id_seq OWNED BY payment_instructions.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payments (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    participant text NOT NULL,
    team text NOT NULL,
    amount numeric(35,2) NOT NULL,
    direction payment_direction NOT NULL,
    payday integer,
    CONSTRAINT positive CHECK ((amount > (0)::numeric))
);


--
-- Name: payments_for_open_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payments_for_open_source (
    uuid text NOT NULL,
    ctime timestamp with time zone DEFAULT now() NOT NULL,
    amount bigint NOT NULL,
    braintree_transaction_id text,
    braintree_result_message text,
    name text NOT NULL,
    follow_up follow_up NOT NULL,
    email_address text NOT NULL,
    promotion_name text DEFAULT ''::text NOT NULL,
    promotion_url text DEFAULT ''::text NOT NULL,
    promotion_twitter text DEFAULT ''::text NOT NULL,
    promotion_message text DEFAULT ''::text NOT NULL,
    grateful_for text DEFAULT ''::text NOT NULL
);


--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payments_id_seq OWNED BY payments.id;


--
-- Name: statements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE statements (
    participant bigint NOT NULL,
    lang text NOT NULL,
    content text NOT NULL,
    search_vector tsvector,
    search_conf regconfig NOT NULL,
    content_scrubbed text DEFAULT ''::text NOT NULL,
    CONSTRAINT statements_content_check CHECK ((content <> ''::text))
);


--
-- Name: takes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE takes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: takes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE takes_id_seq OWNED BY takes.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE teams (
    slug text NOT NULL,
    id bigint NOT NULL,
    ctime timestamp with time zone DEFAULT now() NOT NULL,
    slug_lower text NOT NULL,
    name text NOT NULL,
    homepage text NOT NULL,
    product_or_service text NOT NULL,
    getting_involved text,
    getting_paid text,
    owner text NOT NULL,
    is_closed boolean DEFAULT false NOT NULL,
    is_approved boolean,
    receiving numeric(35,2) DEFAULT 0 NOT NULL,
    nreceiving_from integer DEFAULT 0 NOT NULL,
    distributing numeric(35,2) DEFAULT 0 NOT NULL,
    ndistributing_to integer DEFAULT 0 NOT NULL,
    revenue_model text DEFAULT ''::text,
    onboarding_url text DEFAULT ''::text NOT NULL,
    review_url text,
    image_oid_original oid DEFAULT 0 NOT NULL,
    image_oid_large oid DEFAULT 0 NOT NULL,
    image_oid_small oid DEFAULT 0 NOT NULL,
    image_type supported_image_types,
    available numeric(35,2) DEFAULT 0 NOT NULL,
    CONSTRAINT available_not_negative CHECK ((available >= (0)::numeric))
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE teams_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE teams_id_seq OWNED BY teams.id;


--
-- Name: teams_to_packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE teams_to_packages (
    team_id bigint,
    package_id bigint
);


--
-- Name: tips_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE tips_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE tips_id_seq OWNED BY tips.id;


--
-- Name: transfers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transfers (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    tipper text NOT NULL,
    tippee text NOT NULL,
    amount numeric(35,2) NOT NULL,
    context context_type NOT NULL,
    payday integer
);


--
-- Name: transfers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transfers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transfers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transfers_id_seq OWNED BY transfers.id;


--
-- Name: worker_coordination; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE worker_coordination (
    npm_last_seq bigint DEFAULT '-1'::integer NOT NULL
);


--
-- Name: absorptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY absorptions ALTER COLUMN id SET DEFAULT nextval('absorptions_id_seq'::regclass);


--
-- Name: countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY countries ALTER COLUMN id SET DEFAULT nextval('countries_id_seq'::regclass);


--
-- Name: elsewhere id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY elsewhere ALTER COLUMN id SET DEFAULT nextval('elsewhere_id_seq'::regclass);


--
-- Name: email_addresses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses ALTER COLUMN id SET DEFAULT nextval('emails_id_seq'::regclass);


--
-- Name: email_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_messages ALTER COLUMN id SET DEFAULT nextval('email_queue_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY events ALTER COLUMN id SET DEFAULT nextval('events_id_seq'::regclass);


--
-- Name: exchange_routes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchange_routes ALTER COLUMN id SET DEFAULT nextval('exchange_routes_id_seq'::regclass);


--
-- Name: exchanges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchanges ALTER COLUMN id SET DEFAULT nextval('exchanges_id_seq'::regclass);


--
-- Name: packages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY packages ALTER COLUMN id SET DEFAULT nextval('packages_id_seq'::regclass);


--
-- Name: participant_identities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY participant_identities ALTER COLUMN id SET DEFAULT nextval('participant_identities_id_seq'::regclass);


--
-- Name: participants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants ALTER COLUMN id SET DEFAULT nextval('participants_id_seq'::regclass);


--
-- Name: paydays id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY paydays ALTER COLUMN id SET DEFAULT nextval('paydays_id_seq'::regclass);


--
-- Name: payment_instructions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_instructions ALTER COLUMN id SET DEFAULT nextval('payment_instructions_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments ALTER COLUMN id SET DEFAULT nextval('payments_id_seq'::regclass);


--
-- Name: takes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY takes ALTER COLUMN id SET DEFAULT nextval('takes_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams ALTER COLUMN id SET DEFAULT nextval('teams_id_seq'::regclass);


--
-- Name: tips id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY tips ALTER COLUMN id SET DEFAULT nextval('tips_id_seq'::regclass);


--
-- Name: transfers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers ALTER COLUMN id SET DEFAULT nextval('transfers_id_seq'::regclass);


--
-- Name: absorptions absorptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY absorptions
    ADD CONSTRAINT absorptions_pkey PRIMARY KEY (id);


--
-- Name: balances_at balances_at_participant_at_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY balances_at
    ADD CONSTRAINT balances_at_participant_at_key UNIQUE (participant, at);


--
-- Name: claims claims_nonce_package_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY claims
    ADD CONSTRAINT claims_nonce_package_id_key UNIQUE (nonce, package_id);


--
-- Name: communities communities_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communities
    ADD CONSTRAINT communities_name_key UNIQUE (name);


--
-- Name: communities communities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communities
    ADD CONSTRAINT communities_pkey PRIMARY KEY (slug);


--
-- Name: countries countries_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY countries
    ADD CONSTRAINT countries_code_key UNIQUE (code);


--
-- Name: countries countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY countries
    ADD CONSTRAINT countries_pkey PRIMARY KEY (id);


--
-- Name: elsewhere elsewhere_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY elsewhere
    ADD CONSTRAINT elsewhere_pkey PRIMARY KEY (id);


--
-- Name: elsewhere elsewhere_platform_participant_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY elsewhere
    ADD CONSTRAINT elsewhere_platform_participant_key UNIQUE (platform, participant);


--
-- Name: elsewhere elsewhere_platform_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY elsewhere
    ADD CONSTRAINT elsewhere_platform_user_id_key UNIQUE (platform, user_id);


--
-- Name: email_messages email_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_messages
    ADD CONSTRAINT email_queue_pkey PRIMARY KEY (id);


--
-- Name: email_addresses emails_address_verified_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses
    ADD CONSTRAINT emails_address_verified_key UNIQUE (address, verified);


--
-- Name: email_addresses emails_nonce_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses
    ADD CONSTRAINT emails_nonce_key UNIQUE (nonce);


--
-- Name: email_addresses emails_participant_id_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses
    ADD CONSTRAINT emails_participant_id_address_key UNIQUE (participant_id, address);


--
-- Name: email_addresses emails_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses
    ADD CONSTRAINT emails_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: exchange_routes exchange_routes_participant_network_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchange_routes
    ADD CONSTRAINT exchange_routes_participant_network_address_key UNIQUE (participant, network, address);


--
-- Name: exchange_routes exchange_routes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchange_routes
    ADD CONSTRAINT exchange_routes_pkey PRIMARY KEY (id);


--
-- Name: exchanges exchanges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchanges
    ADD CONSTRAINT exchanges_pkey PRIMARY KEY (id);


--
-- Name: packages packages_package_manager_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY packages
    ADD CONSTRAINT packages_package_manager_name_key UNIQUE (package_manager, name);


--
-- Name: packages packages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY packages
    ADD CONSTRAINT packages_pkey PRIMARY KEY (id);


--
-- Name: participant_identities participant_identities_participant_id_country_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participant_identities
    ADD CONSTRAINT participant_identities_participant_id_country_id_key UNIQUE (participant_id, country_id);


--
-- Name: participant_identities participant_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participant_identities
    ADD CONSTRAINT participant_identities_pkey PRIMARY KEY (id);


--
-- Name: participants participants_email_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants
    ADD CONSTRAINT participants_email_address_key UNIQUE (email_address);


--
-- Name: participants participants_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants
    ADD CONSTRAINT participants_id_key UNIQUE (id);


--
-- Name: participants participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants
    ADD CONSTRAINT participants_pkey PRIMARY KEY (username);


--
-- Name: participants participants_session_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants
    ADD CONSTRAINT participants_session_token_key UNIQUE (session_token);


--
-- Name: participants participants_username_lower_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participants
    ADD CONSTRAINT participants_username_lower_key UNIQUE (username_lower);


--
-- Name: paydays paydays_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY paydays
    ADD CONSTRAINT paydays_pkey PRIMARY KEY (id);


--
-- Name: paydays paydays_ts_end_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY paydays
    ADD CONSTRAINT paydays_ts_end_key UNIQUE (ts_end);


--
-- Name: payment_instructions payment_instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_instructions
    ADD CONSTRAINT payment_instructions_pkey PRIMARY KEY (id);


--
-- Name: payments_for_open_source payments_for_open_source_braintree_transaction_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments_for_open_source
    ADD CONSTRAINT payments_for_open_source_braintree_transaction_id_key UNIQUE (braintree_transaction_id);


--
-- Name: payments_for_open_source payments_for_open_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments_for_open_source
    ADD CONSTRAINT payments_for_open_source_pkey PRIMARY KEY (uuid);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: transfers positive; Type: CHECK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE transfers
    ADD CONSTRAINT positive CHECK ((amount > (0)::numeric)) NOT VALID;


--
-- Name: statements statements_participant_lang_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY statements
    ADD CONSTRAINT statements_participant_lang_key UNIQUE (participant, lang);


--
-- Name: takes takes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY takes
    ADD CONSTRAINT takes_pkey PRIMARY KEY (id);


--
-- Name: teams teams_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams
    ADD CONSTRAINT teams_id_key UNIQUE (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (slug);


--
-- Name: teams teams_slug_lower_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams
    ADD CONSTRAINT teams_slug_lower_key UNIQUE (slug_lower);


--
-- Name: teams_to_packages teams_to_packages_package_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams_to_packages
    ADD CONSTRAINT teams_to_packages_package_id_key UNIQUE (package_id);


--
-- Name: teams_to_packages teams_to_packages_team_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams_to_packages
    ADD CONSTRAINT teams_to_packages_team_id_key UNIQUE (team_id);


--
-- Name: tips tips_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tips
    ADD CONSTRAINT tips_pkey PRIMARY KEY (id);


--
-- Name: transfers transfers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers
    ADD CONSTRAINT transfers_pkey PRIMARY KEY (id);


--
-- Name: community_members_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX community_members_idx ON community_members USING btree (slug, participant, mtime DESC);


--
-- Name: community_trgm_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX community_trgm_idx ON communities USING gist (name gist_trgm_ops);


--
-- Name: elsewhere_participant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX elsewhere_participant ON elsewhere USING btree (participant);


--
-- Name: events_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX events_ts ON events USING btree (ts);


--
-- Name: events_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX events_type ON events USING btree (type);


--
-- Name: participants_claimed_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX participants_claimed_time ON participants USING btree (claimed_time DESC) WHERE ((is_suspicious IS NOT TRUE) AND (claimed_time IS NOT NULL));


--
-- Name: payday_participants_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX payday_participants_id_idx ON payday_participants USING btree (id);


--
-- Name: payday_participants_username_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX payday_participants_username_idx ON payday_participants USING btree (username);


--
-- Name: payday_payment_instructions_participant_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payday_payment_instructions_participant_id_idx ON payday_payment_instructions USING btree (participant_id);


--
-- Name: payday_payment_instructions_team_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payday_payment_instructions_team_id_idx ON payday_payment_instructions USING btree (team_id);


--
-- Name: statements_fts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX statements_fts_idx ON statements USING gist (search_vector);


--
-- Name: tips_all; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tips_all ON tips USING btree (tipper, tippee, mtime DESC);


--
-- Name: transfers_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfers_timestamp_idx ON transfers USING btree ("timestamp");


--
-- Name: transfers_tippee_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfers_tippee_idx ON transfers USING btree (tippee);


--
-- Name: transfers_tipper_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfers_tipper_idx ON transfers USING btree (tipper);


--
-- Name: username_trgm_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX username_trgm_idx ON participants USING gist (username_lower gist_trgm_ops) WHERE ((claimed_time IS NOT NULL) AND (NOT is_closed));


--
-- Name: participant_identities enforce_email_for_participant_identity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER enforce_email_for_participant_identity BEFORE INSERT ON participant_identities FOR EACH ROW EXECUTE PROCEDURE fail_if_no_email();


--
-- Name: payday_teams process_draw; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER process_draw BEFORE UPDATE OF is_drained ON payday_teams FOR EACH ROW WHEN (((new.is_drained IS TRUE) AND (old.is_drained IS NOT TRUE))) EXECUTE PROCEDURE process_draw();


--
-- Name: payday_payment_instructions process_payment_instruction; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER process_payment_instruction BEFORE UPDATE OF is_funded ON payday_payment_instructions FOR EACH ROW WHEN (((new.is_funded IS TRUE) AND (old.is_funded IS NOT TRUE))) EXECUTE PROCEDURE process_payment_instruction();


--
-- Name: payday_takes process_take; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER process_take AFTER INSERT ON payday_takes FOR EACH ROW EXECUTE PROCEDURE process_take();


--
-- Name: statements search_vector_update; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER search_vector_update BEFORE INSERT OR UPDATE ON statements FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger_column('search_vector', 'search_conf', 'content_scrubbed');


--
-- Name: current_payment_instructions update_current_payment_instruction; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_current_payment_instruction INSTEAD OF UPDATE ON current_payment_instructions FOR EACH ROW EXECUTE PROCEDURE update_payment_instruction();


--
-- Name: current_tips update_current_tip; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_current_tip INSTEAD OF UPDATE ON current_tips FOR EACH ROW EXECUTE PROCEDURE update_tip();


--
-- Name: participants update_status_of_1_0_payout; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_status_of_1_0_payout AFTER UPDATE OF balance ON participants FOR EACH ROW WHEN (((old.balance > (0)::numeric) AND (new.balance = (0)::numeric))) EXECUTE PROCEDURE complete_1_0_payout();


--
-- Name: community_members upsert_community; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER upsert_community BEFORE INSERT ON community_members FOR EACH ROW EXECUTE PROCEDURE upsert_community();


--
-- Name: absorptions absorptions_absorbed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY absorptions
    ADD CONSTRAINT absorptions_absorbed_by_fkey FOREIGN KEY (absorbed_by) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: absorptions absorptions_archived_as_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY absorptions
    ADD CONSTRAINT absorptions_archived_as_fkey FOREIGN KEY (archived_as) REFERENCES participants(username) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: balances_at balances_at_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY balances_at
    ADD CONSTRAINT balances_at_participant_fkey FOREIGN KEY (participant) REFERENCES participants(id);


--
-- Name: claims claims_nonce_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY claims
    ADD CONSTRAINT claims_nonce_fkey FOREIGN KEY (nonce) REFERENCES email_addresses(nonce) ON UPDATE RESTRICT ON DELETE CASCADE;


--
-- Name: claims claims_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY claims
    ADD CONSTRAINT claims_package_id_fkey FOREIGN KEY (package_id) REFERENCES packages(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: community_members community_members_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY community_members
    ADD CONSTRAINT community_members_participant_fkey FOREIGN KEY (participant) REFERENCES participants(id);


--
-- Name: elsewhere elsewhere_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY elsewhere
    ADD CONSTRAINT elsewhere_participant_fkey FOREIGN KEY (participant) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: email_messages email_queue_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_messages
    ADD CONSTRAINT email_queue_participant_fkey FOREIGN KEY (participant) REFERENCES participants(id);


--
-- Name: email_addresses emails_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_addresses
    ADD CONSTRAINT emails_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: exchange_routes exchange_routes_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchange_routes
    ADD CONSTRAINT exchange_routes_participant_fkey FOREIGN KEY (participant) REFERENCES participants(id);


--
-- Name: exchanges exchanges_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchanges
    ADD CONSTRAINT exchanges_participant_fkey FOREIGN KEY (participant) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: exchanges exchanges_recorder_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchanges
    ADD CONSTRAINT exchanges_recorder_fkey FOREIGN KEY (recorder) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: exchanges exchanges_route_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY exchanges
    ADD CONSTRAINT exchanges_route_fkey FOREIGN KEY (route) REFERENCES exchange_routes(id);


--
-- Name: participant_identities participant_identities_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participant_identities
    ADD CONSTRAINT participant_identities_country_id_fkey FOREIGN KEY (country_id) REFERENCES countries(id);


--
-- Name: participant_identities participant_identities_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY participant_identities
    ADD CONSTRAINT participant_identities_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES participants(id);


--
-- Name: payment_instructions payment_instructions_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_instructions
    ADD CONSTRAINT payment_instructions_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: payment_instructions payment_instructions_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_instructions
    ADD CONSTRAINT payment_instructions_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: payments payments_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments
    ADD CONSTRAINT payments_participant_fkey FOREIGN KEY (participant) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: payments payments_payday_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments
    ADD CONSTRAINT payments_payday_fkey FOREIGN KEY (payday) REFERENCES paydays(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: payments payments_team_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payments
    ADD CONSTRAINT payments_team_fkey FOREIGN KEY (team) REFERENCES teams(slug) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: statements statements_participant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY statements
    ADD CONSTRAINT statements_participant_fkey FOREIGN KEY (participant) REFERENCES participants(id);


--
-- Name: takes takes_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY takes
    ADD CONSTRAINT takes_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES participants(id);


--
-- Name: takes takes_recorder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY takes
    ADD CONSTRAINT takes_recorder_id_fkey FOREIGN KEY (recorder_id) REFERENCES participants(id);


--
-- Name: takes takes_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY takes
    ADD CONSTRAINT takes_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id);


--
-- Name: teams teams_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams
    ADD CONSTRAINT teams_owner_fkey FOREIGN KEY (owner) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: teams_to_packages teams_to_packages_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams_to_packages
    ADD CONSTRAINT teams_to_packages_package_id_fkey FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE RESTRICT;


--
-- Name: teams_to_packages teams_to_packages_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY teams_to_packages
    ADD CONSTRAINT teams_to_packages_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT;


--
-- Name: tips tips_tippee_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tips
    ADD CONSTRAINT tips_tippee_fkey FOREIGN KEY (tippee) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: tips tips_tipper_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY tips
    ADD CONSTRAINT tips_tipper_fkey FOREIGN KEY (tipper) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: transfers transfers_payday_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers
    ADD CONSTRAINT transfers_payday_fkey FOREIGN KEY (payday) REFERENCES paydays(id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- Name: transfers transfers_tippee_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers
    ADD CONSTRAINT transfers_tippee_fkey FOREIGN KEY (tippee) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: transfers transfers_tipper_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers
    ADD CONSTRAINT transfers_tipper_fkey FOREIGN KEY (tipper) REFERENCES participants(username) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

