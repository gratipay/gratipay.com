"""This module contains utilities for populating a non-production environment with fake data.
"""
import datetime
from decimal import Decimal as D
import random
import string
import sys
from collections import defaultdict

from faker import Factory
from psycopg2 import IntegrityError

from gratipay import wireup, MAX_TIP, MIN_TIP
from gratipay.elsewhere import PLATFORMS
from gratipay.models.participant import Participant
from gratipay.models.team import slugize, Team
from gratipay.models import check_db
from gratipay.exceptions import InvalidTeamName

faker = Factory.create()


def insert_fake_data(db, tablename, **kw):
    """Insert fake data into the database.

    :param Postgres db: a ``Postgres`` or ``Cursor`` object
    :param unicode tablename: the name of the table to insert into
    :param dict kw: a mapping of column names to values

    """
    column_names = []
    column_value_placeholders = []
    column_values = []

    for k,v in kw.items():
        column_names.append(k)
        column_value_placeholders.append("%s")
        column_values.append(v)

    column_names = ", ".join(column_names)
    column_value_placeholders = ", ".join(column_value_placeholders)

    db.run( "INSERT INTO {} ({}) VALUES ({})"
            .format(tablename, column_names, column_value_placeholders)
          , column_values
           )
    return kw


def fake_text_id(size=6, chars=string.ascii_lowercase + string.digits):
    """Create a random text id.
    """
    return ''.join(random.choice(chars) for x in range(size))


def fake_sentence(start=1, stop=100):
    """Create a sentence of random length.
    """
    return faker.sentence(random.randrange(start,stop))


def fake_participant(db, is_admin=False, random_identities=True):
    """Create a fake User.

    :param Postgres db: a ``Postgres`` or ``Cursor`` object
    :param bool is_admin: whether to make the participant an admin
    :param bool random_identities: whether to give the participant random identities

    """
    username = faker.first_name() + fake_text_id(3)
    try:
        insert_fake_data( db
                        , "participants"
                        , username=username
                        , username_lower=username.lower()
                        , ctime=faker.date_time_this_year()
                        , is_admin=is_admin
                        , balance=0
                        , anonymous_giving=(random.randrange(5) == 0)
                        , balanced_customer_href=faker.uri()
                        , is_suspicious=False
                        , claimed_time=faker.date_time_this_year()
                        , email_address='{}@example.com'.format(username)
                         )
        participant = Participant.from_username(username)

        fake_exchange_route(db, participant)
        if random_identities:
            if random.randrange(100) < 66:
                fake_participant_identity(participant)
                if random.randrange(100) < 33:
                    fake_participant_identity(participant)
                    if random.randrange(100) < 50:
                        fake_participant_identity(participant)

    except IntegrityError:
        return fake_participant(db, is_admin)

    return participant


def fake_exchange_route(db, participant, network=None):
    
    if not network:
        networks = ["balanced-ba", "balanced-cc", "paypal", "bitcoin"]
        network = random.sample(networks, 1)[0]

    insert_fake_data( db
                    , "exchange_routes"
                    , participant = participant.id
                    , network = network 
                    , address = participant.email_address
                    , error = "None" 
                    )
        

def fake_participant_identity(participant, verification=None):
    """Pick a country and make an identity for the participant there.

    :param Participant participant: a participant object
    :param bool verification: the value to set verification to; None will result in a 50% chance
        either way
    :returns: a country id

    """
    country_id = random_country_id(participant.db)
    participant.store_identity_info(country_id, 'nothing-enforced', {})
    if verification:
        participant.set_identity_verification(country_id, verification)
    elif (random.randrange(2) == 0):   # 50%
        participant.set_identity_verification(country_id, True)
    return country_id


def fake_team(db, teamowner, teamname=None):
    """Create a fake team
    """
    isapproved = [True, False]
    productorservice = ['Product','Service']

    if teamname is None:
        teamname = faker.first_name() + fake_text_id(3)
    
    try:
        teamslug = slugize(teamname)
        homepage = 'http://www.example.org/' + fake_text_id(3)
        insert_fake_data( db
                        , "teams"
                        , slug=teamslug
                        , slug_lower=teamslug.lower()
                        , name=teamname
                        , homepage=homepage
                        , product_or_service=random.sample(productorservice,1)[0]
                        , todo_url=homepage + '/tickets'
                        , onboarding_url=homepage + '/contributing'
                        , owner=teamowner.username
                        , is_approved=random.sample(isapproved,1)[0]
                        , receiving=0.1
                        , nreceiving_from=3
                         )
    except (IntegrityError, InvalidTeamName):
        return fake_team(db, teamowner)

    return Team.from_slug(teamslug)


def fake_payment_instruction(db, participant, team):
    """Create a fake payment_instruction
    """
    return insert_fake_data( db
                           , "payment_instructions"
                           , ctime=faker.date_time_this_year()
                           , mtime=faker.date_time_this_month()
                           , participant_id=participant.id
                           , team_id=team.id
                           , amount=fake_tip_amount()
                            )


def fake_tip_amount():
    amount = ((D(random.random()) * (MAX_TIP - MIN_TIP))
            + MIN_TIP)

    decimal_amount = D(amount).quantize(D('.01'))
    while decimal_amount == D('0.00'):
        # https://github.com/gratipay/gratipay.com/issues/2950
        decimal_amount = fake_tip_amount()
    return decimal_amount


def fake_tip(db, tipper, tippee):
    """Create a fake tip.
    """
    return insert_fake_data( db
                           , "tips"
                           , ctime=faker.date_time_this_year()
                           , mtime=faker.date_time_this_month()
                           , tipper=tipper.username
                           , tippee=tippee.username
                           , amount=fake_tip_amount()
                            )


def fake_elsewhere(db, participant, platform):
    """Create a fake elsewhere.
    """
    insert_fake_data( db
                    , "elsewhere"
                    , platform=platform
                    , user_id=fake_text_id()
                    , user_name=participant.username
                    , participant=participant.username
                    , extra_info=None
                     )

def fake_payment(db, participant, team, amount, direction):
    """Create fake payment
    """
    return insert_fake_data( db
                            , "payments"
                            , timestamp=faker.date_time_this_year()
                            , participant=participant
                            , team=team
                            , amount=amount
                            , direction=direction
                            )

def fake_transfer(db, tipper, tippee):
    return insert_fake_data( db
                           , "transfers"
                           , timestamp=faker.date_time_this_year()
                           , tipper=tipper.username
                           , tippee=tippee.username
                           , amount=fake_tip_amount()
                           , context='tip'
                            )


def fake_exchange(db, participant, amount, fee, timestamp):
    return insert_fake_data( db
                           , "exchanges"
                           , timestamp=timestamp
                           , participant=participant.username
                           , amount=amount
                           , fee=fee
                           , status='succeeded'
                           , route=get_exchange_route(db, participant.id)
                            )


def get_exchange_route(db, participant):
    return db.one("SELECT id FROM exchange_routes WHERE participant={}"
                    .format(participant), participant)

def random_country_id(db):
    return db.one("SELECT id FROM countries ORDER BY random() LIMIT 1")



def prep_db(db):
    db.run("""
        CREATE OR REPLACE FUNCTION process_transfer() RETURNS trigger AS $$
            BEGIN
                UPDATE participants
                   SET balance = balance + NEW.amount
                 WHERE username = NEW.tippee;

                UPDATE participants
                   SET balance = balance - NEW.amount
                 WHERE username = NEW.tipper;

                RETURN NULL;
            END;
        $$ language plpgsql;

        CREATE TRIGGER process_transfer AFTER INSERT ON transfers
            FOR EACH ROW EXECUTE PROCEDURE process_transfer();

        CREATE OR REPLACE FUNCTION process_payment() RETURNS trigger AS $$
            BEGIN
                UPDATE participants
                   SET balance = balance + NEW.amount
                 WHERE username = NEW.participant
                   AND NEW.direction = 'to-participant';

                UPDATE participants
                   SET balance = balance - NEW.amount
                 WHERE username = NEW.participant
                   AND NEW.direction = 'to-team';

                RETURN NULL;
            END;
        $$ language plpgsql;

        CREATE TRIGGER process_payment AFTER INSERT ON payments
            FOR EACH ROW EXECUTE PROCEDURE process_payment();

        CREATE OR REPLACE FUNCTION process_exchange() RETURNS trigger AS $$
            BEGIN
                IF NEW.amount > 0 THEN
                    UPDATE participants
                       SET balance = balance + NEW.amount
                     WHERE username = NEW.participant;
                ELSE
                    UPDATE participants
                       SET balance = balance + NEW.amount - NEW.fee
                     WHERE username = NEW.participant;
                END IF;

                RETURN NULL;
            END;
        $$ language plpgsql;

        CREATE TRIGGER process_exchange AFTER INSERT ON exchanges
            FOR EACH ROW EXECUTE PROCEDURE process_exchange();
    """)


def clean_db(db):
    db.run("""
        DROP FUNCTION IF EXISTS process_transfer() CASCADE;
        DROP FUNCTION IF EXISTS process_exchange() CASCADE;
        DROP FUNCTION IF EXISTS process_payment() CASCADE;
        """)

def populate_db(db, num_participants=100, ntips=200, num_teams=5, num_transfers=5000):
    """Populate DB with fake data.
    """
    print("Making Participants")
    make_flag_tester = num_participants > 1

    participants = []
    for i in xrange(num_participants - 1 if make_flag_tester else num_participants):
        participants.append(fake_participant(db))

    if make_flag_tester:
        # make a participant for testing weird flags
        flag_tester = fake_participant(db, random_identities=False)
        participants.append(flag_tester)

        nepal = db.one("SELECT id FROM countries WHERE code='NP'")
        flag_tester.store_identity_info(nepal, 'nothing-enforced', {})
        flag_tester.set_identity_verification(nepal, True)

        vatican = db.one("SELECT id FROM countries WHERE code='VA'")
        flag_tester.store_identity_info(vatican, 'nothing-enforced', {})
        flag_tester.set_identity_verification(vatican, True)

    print("Making Teams")
    teams = []
    teamowners = random.sample(participants, num_teams)
    for teamowner in teamowners:
        teams.append(fake_team(db, teamowner))
        
    # Creating a fake Gratipay Team 
    teamowner = random.choice(participants) 
    teams.append(fake_team(db, teamowner, "Gratipay"))

    print("Making Payment Instructions")
    npayment_instructions = 0
    payment_instructions = []
    for participant in participants:
        for team in teams:
            #eliminate self-payment
            if participant.username != team.owner:
                npayment_instructions += 1
                if npayment_instructions > ntips:
                    break
                payment_instructions.append(fake_payment_instruction(db, participant, team))
        if npayment_instructions > ntips:
            break

    print("Making Elsewheres")
    for p in participants:
        #All participants get between 1 and 3 elsewheres
        num_elsewheres = random.randint(1, 3)
        for platform_name in random.sample(PLATFORMS, num_elsewheres):
            fake_elsewhere(db, p, platform_name)


    print("Making Tips")
    tips = []
    for i in xrange(ntips):
        tipper, tippee = random.sample(participants, 2)
        tips.append(fake_tip(db, tipper, tippee))

    # Payments
    payments = []
    paymentcount = 0
    team_amounts = defaultdict(int)
    for payment_instruction in payment_instructions:
        participant = Participant.from_id(payment_instruction['participant_id'])
        team = Team.from_id(payment_instruction['team_id'])
        amount = payment_instruction['amount']
        assert participant.username != team.owner
        paymentcount += 1
        sys.stdout.write("\rMaking Payments (%i)" % (paymentcount))
        sys.stdout.flush()
        payments.append(fake_payment(db, participant.username, team.slug, amount, 'to-team'))
        team_amounts[team.slug] += amount
    for team in teams:
        paymentcount += 1
        sys.stdout.write("\rMaking Payments (%i)" % (paymentcount))
        sys.stdout.flush()
        payments.append(fake_payment(db, team.owner, team.slug, team_amounts[team.slug], 'to-participant'))
    print("")

    # Transfers
    transfers = []
    for i in xrange(num_transfers):
        sys.stdout.write("\rMaking Transfers (%i/%i)" % (i+1, num_transfers))
        sys.stdout.flush()
        tipper, tippee = random.sample(participants, 2)
        transfers.append(fake_transfer(db, tipper, tippee))
    print("")

    # Paydays
    # First determine the boundaries - min and max date
    min_date = min(min(x['ctime'] for x in payment_instructions + tips),
                   min(x['timestamp'] for x in payments + transfers))
    max_date = max(max(x['ctime'] for x in payment_instructions + tips),
                   max(x['timestamp'] for x in payments + transfers))
    # iterate through min_date, max_date one week at a time
    payday_counter = 1
    date = min_date
    paydays_total = (max_date - min_date).days/7 + 1
    while date < max_date:
        sys.stdout.write("\rMaking Paydays (%i/%i)" % (payday_counter, paydays_total))
        sys.stdout.flush()
        payday_counter += 1
        end_date = date + datetime.timedelta(days=7)
        week_tips = filter(lambda x: date <= x['ctime'] < end_date, tips)
        week_transfers = filter(lambda x: date <= x['timestamp'] < end_date, transfers)
        week_payment_instructions = filter(lambda x: date <= x['ctime'] < end_date, payment_instructions)
        week_payments = filter(lambda x: date <= x['timestamp'] < end_date, payments)
        week_payments_to_teams = filter(lambda x: x['direction'] == 'to-team', week_payments)
        week_payments_to_owners = filter(lambda x: x['direction'] == 'to-participant', week_payments)
        for p in participants:
            transfers_in = filter(lambda x: x['tippee'] == p.username, week_transfers)
            payments_in = filter(lambda x: x['participant'] == p.username, week_payments_to_owners)
            transfers_out = filter(lambda x: x['tipper'] == p.username, week_transfers)
            payments_out = filter(lambda x: x['participant'] == p.username, week_payments_to_teams)
            amount_in = sum([t['amount'] for t in transfers_in + payments_in])
            amount_out = sum([t['amount'] for t in transfers_out + payments_out])
            amount = amount_out - amount_in
            fee = amount * D('0.02')
            fee = abs(fee.quantize(D('.01')))
            if amount != 0:
                fee = amount * D('0.02')
                fee = abs(fee.quantize(D('.01')))
                fake_exchange(
                    db=db,
                    participant=p,
                    amount=amount,
                    fee=fee,
                    timestamp=(end_date - datetime.timedelta(seconds=1))
                )
        actives=set()
        tippers=set()
        #week_tips, week_transfers
        for xfers in week_tips, week_transfers:
            actives.update(x['tipper'] for x in xfers)
            actives.update(x['tippee'] for x in xfers)
            tippers.update(x['tipper'] for x in xfers)

        # week_payment_instructions
        actives.update(x['participant_id'] for x in week_payment_instructions)
        tippers.update(x['participant_id'] for x in week_payment_instructions)

        # week_payments
        actives.update(x['participant'] for x in week_payments)
        tippers.update(x['participant'] for x in week_payments_to_owners)

        payday = {
            'ts_start': date,
            'ts_end': end_date,
            'nusers': len(actives),
            'volume': sum(x['amount'] for x in week_transfers)
        }
        insert_fake_data(db, "paydays", **payday)
        date = end_date
    print("")


def _wireup():
    env = wireup.env()
    db = wireup.db(env)
    wireup.crypto(env)
    return db


def main(db=None, *a, **kw):
    db = db or _wireup()
    clean_db(db)
    prep_db(db)
    populate_db(db, *a, **kw)
    clean_db(db)
    check_db(db)


if __name__ == '__main__':
    main()
