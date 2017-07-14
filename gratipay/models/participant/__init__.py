"""Participants on Gratipay give payments and take payouts.
"""
from __future__ import print_function, unicode_literals

from decimal import Decimal
import uuid

from aspen.utils import utcnow
from dependency_injection import resolve_dependencies
from postgres.orm import Model
from psycopg2 import IntegrityError

import gratipay
from gratipay.exceptions import (
    NotSane,
    UsernameIsEmpty,
    UsernameTooLong,
    UsernameContainsInvalidCharacters,
    UsernameIsRestricted,
    UsernameAlreadyTaken,
    BadAmount,
)

from gratipay.models.account_elsewhere import AccountElsewhere
from gratipay.models.team import Team
from gratipay.models.team.takes import ZERO
from gratipay.utils import (
    i18n,
    markdown,
    notifications,
    pricing,
)
from gratipay.utils.username import safely_reserve_a_username

from .email import Email
from .exchange_routes import ExchangeRoutes
from .identity import Identity
from .packages import Packages

MAX_TIP = MAX_PAYMENT = Decimal('1000.00')
MIN_TIP = MIN_PAYMENT = Decimal('0.00')

ASCII_ALLOWED_IN_USERNAME = set("0123456789"
                                "abcdefghijklmnopqrstuvwxyz"
                                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                ".,_:@ -")
# We use | in Sentry logging, so don't make that allowable. :-)

USERNAME_MAX_SIZE = 32


class Participant(Model, Email, ExchangeRoutes, Identity, Packages):
    """Represent a Gratipay participant.
    """

    typname = 'participants'

    def __eq__(self, other):
        if not isinstance(other, Participant):
            return False
        return self.id == other.id

    def __ne__(self, other):
        if not isinstance(other, Participant):
            return True
        return self.id != other.id

    def __repr__(self):
        return '<Participant %s>' % repr(self.username)


    # Constructors
    # ============

    @classmethod
    def with_random_username(cls):
        """Return a new participant with a random username.
        """
        with cls.db.get_cursor() as cursor:
            username = safely_reserve_a_username(cursor)
        return cls.from_username(username)

    @classmethod
    def from_id(cls, id):
        """Return an existing participant based on id.
        """
        return cls._from_thing("id", id)

    @classmethod
    def from_username(cls, username):
        """Return an existing participant based on username.
        """
        return cls._from_thing("username_lower", username.lower())

    @classmethod
    def from_session_token(cls, token):
        """Return an existing participant based on session token.
        """
        participant = cls._from_thing("session_token", token)
        if participant and participant.session_expires < utcnow():
            participant = None

        return participant

    @classmethod
    def from_email(cls, email_address):
        """Return an existing participant based on email.
        """
        return cls.db.one("""

            SELECT participants.*::participants
              FROM participants
              JOIN emails ON emails.participant_id = participants.id
             WHERE emails.address=%s
               AND emails.verified IS true

        """, (email_address, ))

    @classmethod
    def _from_thing(cls, thing, value):
        assert thing in ("id", "username_lower", "session_token", "api_key")
        return cls.db.one("""

            SELECT participants.*::participants
              FROM participants
             WHERE {}=%s

        """.format(thing), (value,))


    # URLs
    # ====

    @property
    def url_path(self):
        """The path part of the URL for this participant on Gratipay.
        """
        return '/~{}/'.format(self.username)


    # Session Management
    # ==================

    def update_session(self, new_token, expires):
        """Set ``session_token`` and ``session_expires``.

        :database: One UPDATE, one row

        """
        self.db.run("""
            UPDATE participants
               SET session_token=%s
                 , session_expires=%s
             WHERE id=%s
               AND is_suspicious IS NOT true
        """, (new_token, expires, self.id))
        self.set_attributes(session_token=new_token, session_expires=expires)

    def set_session_expires(self, expires):
        """Set ``session_expires`` to the given datetime.

        :database: One UPDATE, one row

        """
        self.db.run( "UPDATE participants SET session_expires=%s "
                     "WHERE id=%s AND is_suspicious IS NOT true"
                   , (expires, self.id,)
                    )
        self.set_attributes(session_expires=expires)


    # Suspiciousness
    # ==============

    @property
    def is_whitelisted(self):
        return self.is_suspicious is False


    # Claimed-ness
    # ============

    @property
    def is_claimed(self):
        return self.claimed_time is not None

    @property
    def closed_time(self):
        return self.db.one("""
            SELECT ts AT TIME ZONE 'UTC'
              FROM events
             WHERE payload->>'id'=%s
               AND payload->>'action'='set'
               AND payload->'values'->>'is_closed'='true'
          ORDER BY ts DESC
             LIMIT 1
        """, (str(self.id),))


    # Statement
    # =========

    def get_statement(self, langs, scrubbed=False):
        """Get the participant's statement in the language that best matches
        the list provided.
        """
        content, content_scrubbed, lang = self.db.one("""
            SELECT content, content_scrubbed, lang
              FROM statements
              JOIN enumerate(%(langs)s) langs ON langs.value = statements.lang
             WHERE participant=%(id)s
          ORDER BY langs.rank
             LIMIT 1
        """, dict(id=self.id, langs=langs), default=(None, None, None))
        return (content_scrubbed if scrubbed else content, lang)

    def get_statement_langs(self):
        return self.db.all("SELECT lang FROM statements WHERE participant=%s",
                           (self.id,))

    def upsert_statement(self, lang, statement):
        if not statement:
            self.db.run("DELETE FROM statements WHERE participant=%s AND lang=%s",
                        (self.id, lang))
            return
        scrubbed = markdown.render_and_scrub(statement)
        r = self.db.one("""
            UPDATE statements
               SET content=%s
                 , content_scrubbed=%s
             WHERE participant=%s
               AND lang=%s
         RETURNING true
        """, (statement, scrubbed, self.id, lang))
        if not r:
            search_conf = i18n.SEARCH_CONFS.get(lang, 'simple')
            try:
                self.db.run("""
                    INSERT INTO statements
                                (lang, content, content_scrubbed, participant, search_conf)
                         VALUES (%s, %s, %s, %s, %s)
                """, (lang, statement, scrubbed, self.id, search_conf))
            except IntegrityError:
                return self.upsert_statement(lang, statement)


    # Pricing
    # =======

    @property
    def usage(self):
        return max(self.giving, self.taking)

    @property
    def suggested_payment(self):
        return pricing.suggested_payment(self.usage)

    @property
    def suggested_payment_low_high(self):
        return pricing.suggested_payment_low_high(self.usage)


    # API Key
    # =======

    def recreate_api_key(self):
        api_key = self._generate_api_key()
        SQL = "UPDATE participants SET api_key=%s WHERE username=%s RETURNING api_key"
        with self.db.get_cursor() as c:
            self.app.add_event( c
                              , 'participant'
                              , dict(action='set', id=self.id, values=dict(api_key=api_key))
                               )
            api_key = c.one(SQL, (api_key, self.username))
        self.set_attributes(api_key=api_key)
        return api_key

    def _generate_api_key(self):
        return str(uuid.uuid4())


    # Claiming
    # ========
    # An unclaimed Participant is a stub that's created when someone visits our
    # page for an AccountElsewhere that's not been connected on Gratipay yet.

    def resolve_unclaimed(self):
        """Given a username, return an URL path.
        """
        rec = self.db.one("""
            SELECT platform, user_name
              FROM elsewhere
             WHERE participant = %s
        """, (self.username,))
        return rec and '/on/%s/%s/' % (rec.platform, rec.user_name)

    def set_as_claimed(self):
        with self.db.get_cursor() as c:
            self.app.add_event(c, 'participant', dict(id=self.id, action='claim'))
            claimed_time = c.one("""\

                UPDATE participants
                   SET claimed_time=CURRENT_TIMESTAMP
                 WHERE username=%s
                   AND claimed_time IS NULL
             RETURNING claimed_time

            """, (self.username,))
            self.set_attributes(claimed_time=claimed_time)


    # Closing
    # =======

    def close(self, require_zero_balance=True):
        """Close the participant's account.
        """
        with self.db.get_cursor() as cursor:
            self.clear_payment_instructions(cursor)
            self.clear_personal_information(cursor)
            self.final_check(cursor, require_zero_balance)
            self.update_is_closed(True, cursor)

    def update_is_closed(self, is_closed, cursor=None):
        with self.db.get_cursor(cursor) as cursor:
            cursor.run( "UPDATE participants SET is_closed=%(is_closed)s "
                        "WHERE username=%(username)s"
                      , dict(username=self.username, is_closed=is_closed)
                       )
            self.app.add_event( cursor
                              , 'participant'
                              , dict(id=self.id, action='set', values=dict(is_closed=is_closed))
                               )
            self.set_attributes(is_closed=is_closed)


    def clear_payment_instructions(self, cursor):
        """Zero out the participant's payment_instructions.
        """
        teams = cursor.all("""

            SELECT ( SELECT teams.*::teams
                       FROM teams
                      WHERE id=team_id
                    ) AS team
              FROM current_payment_instructions
             WHERE participant_id = %s
               AND amount > 0

        """, (self.id,))
        for team in teams:
            self.set_payment_instruction(team, '0.00', update_self=False, cursor=cursor)


    def clear_takes(self, cursor):
        """Leave all teams by zeroing all takes.
        """
        for team in self.get_teams():
            # `get_teams` returns teams that a participant is either a member or owner of.
            #
            # Owners don't necessarily have takes, so we filter out those cases before setting
            # their take to zero.
            if self.member_of(team):
                team.set_take_for(self, ZERO, recorder=self, cursor=cursor)


    def clear_personal_information(self, cursor):
        """Clear personal information such as statements.
        """
        r = cursor.one("""

            INSERT INTO community_members (slug, participant, ctime, name, is_member) (
                SELECT slug, participant, ctime, name, false
                  FROM community_members
                 WHERE participant=%(participant_id)s
                   AND is_member IS true
            );

            DELETE FROM emails WHERE participant_id = %(participant_id)s;
            DELETE FROM statements WHERE participant=%(participant_id)s;
            DELETE FROM participant_identities WHERE participant_id=%(participant_id)s;

            UPDATE participants
               SET anonymous_giving=False
                 , avatar_url=NULL
                 , email_address=NULL
                 , claimed_time=NULL
                 , session_token=NULL
                 , session_expires=now()
                 , giving=0
                 , taking=0
             WHERE username=%(username)s
         RETURNING *;

        """, dict(username=self.username, participant_id=self.id))
        self.set_attributes(**r._asdict())


    # Notifications
    # =============

    def add_notification(self, name):
        id = self.id
        r = self.db.one("""
            UPDATE participants
               SET notifications = array_append(notifications, %(name)s)
             WHERE id = %(id)s
               AND NOT %(name)s = ANY(notifications);

            SELECT notifications
              FROM participants
             WHERE id = %(id)s;
        """, locals())
        self.set_attributes(notifications=r)

    def add_signin_notifications(self):
        if not self.get_emails():
            self.add_notification('email_missing')
        if self.get_paypal_error():
            self.add_notification('paypal_withdrawal_failed')
        if self.get_credit_card_error():
            self.add_notification('credit_card_failed')
        elif self.credit_card_expiring():
            self.add_notification('credit_card_expires')

    def remove_notification(self, name):
        id = self.id
        r = self.db.one("""
            UPDATE participants
               SET notifications = array_remove(notifications, %(name)s)
             WHERE id = %(id)s
         RETURNING notifications
        """, locals())
        self.set_attributes(notifications=r)

    def render_notifications(self, state):
        r = []
        escape = state['escape']
        state['escape'] = lambda a: a
        for name in self.notifications:
            try:
                f = getattr(notifications, name)
                typ, msg = f(*resolve_dependencies(f, state).as_args)
                r.append(dict(jsonml=msg, name=name, type=typ))
            except Exception as e:
                self._tell_sentry(e, state)
        state['escape'] = escape
        return r


    # Elsewhere-related stuff
    # =======================

    def get_account_elsewhere(self, platform):
        """Return an AccountElsewhere instance.
        """
        return self.db.one("""

            SELECT elsewhere.*::elsewhere_with_participant
              FROM elsewhere
             WHERE participant=%s
               AND platform=%s

        """, (self.username, platform))


    def get_accounts_elsewhere(self):
        """Return a dict of AccountElsewhere instances.
        """
        accounts = self.db.all("""

            SELECT elsewhere.*::elsewhere_with_participant
              FROM elsewhere
             WHERE participant=%s

        """, (self.username,))
        accounts_dict = {account.platform: account for account in accounts}
        return accounts_dict


    def get_elsewhere_logins(self, cursor):
        """Return the list of (platform, user_id) tuples that the participant
        can log in with.
        """
        return cursor.all("""
            SELECT platform, user_id
              FROM elsewhere
             WHERE participant=%s
               AND platform IN %s
               AND NOT is_team
        """, (self.username, AccountElsewhere.signin_platforms_names))

    def delete_elsewhere(self, platform, user_id):
        """Deletes account elsewhere unless the user would not be able
        to log in anymore.
        """
        user_id = unicode(user_id)
        with self.db.get_cursor() as c:
            accounts = self.get_elsewhere_logins(c)
            assert len(accounts) > 0
            if len(accounts) == 1 and accounts[0] == (platform, user_id):
                raise LastElsewhere()
            c.one("""
                DELETE FROM elsewhere
                WHERE participant=%s
                AND platform=%s
                AND user_id=%s
                RETURNING participant
            """, (self.username, platform, user_id), default=NonexistingElsewhere)
            self.app.add_event( c
                              , 'participant'
                              , dict( id=self.id
                                    , action='disconnect'
                                    , values=dict(platform=platform, user_id=user_id)
                                     )
                               )
        self.update_avatar()

    def update_avatar(self):
        avatar_url = self.db.run("""
            UPDATE participants p
               SET avatar_url = (
                       SELECT avatar_url
                         FROM elsewhere
                        WHERE participant = p.username
                     ORDER BY platform = 'github' DESC,
                              avatar_url LIKE '%%gravatar.com%%' DESC
                        LIMIT 1
                   )
             WHERE p.username = %s
         RETURNING avatar_url
        """, (self.username,))
        self.set_attributes(avatar_url=avatar_url)


    # Giving and Taking
    # =================

    def set_payment_instruction(self, team, amount, update_self=True, update_team=True,
                                                                                      cursor=None):
        """Given a Team instance, and amount as str, return a dict.

        We INSERT instead of UPDATE, so that we have history to explore. The
        COALESCE function returns the first of its arguments that is not NULL.
        The effect here is to stamp all payment instructions with the timestamp
        of the first instruction from this ~user to that Team. I believe this
        is used to determine the order of payments during payday.

        The dict returned represents the row inserted in the payment_instructions
        table.

        """
        assert self.is_claimed  # sanity check

        amount = Decimal(amount)  # May raise InvalidOperation
        if (amount < MIN_PAYMENT) or (amount > MAX_PAYMENT):
            raise BadAmount

        # Insert payment instruction
        NEW_PAYMENT_INSTRUCTION = """\

            INSERT INTO payment_instructions
                        (ctime, participant_id, team_id, amount)
                 VALUES ( COALESCE (( SELECT ctime
                                        FROM payment_instructions
                                       WHERE (   participant_id=%(participant_id)s
                                             AND team_id=%(team_id)s
                                              )
                                       LIMIT 1
                                      ), CURRENT_TIMESTAMP)
                        , %(participant_id)s, %(team_id)s, %(amount)s
                         )
              RETURNING *

        """
        args = dict(participant_id=self.id, team_id=team.id, amount=amount)
        t = (cursor or self.db).one(NEW_PAYMENT_INSTRUCTION, args)
        t_dict = t._asdict()

        if amount > 0:
            # Carry over any existing due
            self._update_due(t_dict['team_id'], t_dict['id'], cursor)
        else:
            self._reset_due(t_dict['team_id'], cursor=cursor)

        if update_self:
            # Update giving amount of participant
            self.update_giving(cursor)
        if update_team:
            # Update receiving amount of team
            team.update_receiving(cursor)
        if team.slug == 'Gratipay':
            # Update whether the participant is using Gratipay for free
            self.update_is_free_rider(None if amount == 0 else False, cursor)

        return t._asdict()


    def get_payment_instruction(self, team):
        """Given a Team instance, return a dict.
        """
        default = dict(amount=Decimal('0.00'), is_funded=False)
        return self.db.one("""\

            SELECT *
              FROM payment_instructions
             WHERE participant_id=%s
               AND team_id=%s
          ORDER BY mtime DESC
             LIMIT 1

        """, (self.id, team.id), back_as=dict, default=default)


    def get_due(self, team):
        """Given a Team instance, return a Decimal.
        """
        return self.db.one("""\

            SELECT due
              FROM current_payment_instructions
             WHERE participant_id = %s
               AND team_id = %s

        """, (self.id, team.id))


    def get_giving_for_profile(self):
        """Return a list and a Decimal.
        """

        GIVING = """\

            SELECT * FROM (
                SELECT DISTINCT ON (pi.team_id)
                       t.slug AS team_slug
                     , pi.amount
                     , pi.due
                     , pi.ctime
                     , pi.mtime
                     , t.name   AS team_name
                  FROM payment_instructions pi
                  JOIN teams t ON pi.team_id = t.id
                 WHERE participant_id = %s
                   AND t.is_approved is true
                   AND t.is_closed is not true
              ORDER BY pi.team_id
                     , pi.mtime DESC
            ) AS foo
            ORDER BY amount DESC
                   , team_slug

        """
        giving = self.db.all(GIVING, (self.id,))


        # Compute the totals.
        # ==================

        totals = {
            'amount': sum([rec.amount for rec in giving]) or Decimal('0.00'),
            'due': sum([rec.due for rec in giving]) or Decimal('0.00')
        }

        return giving, totals


    def get_old_stats(self):
        """Returns a tuple: (sum, number) of old-style 1.0 tips.
        """
        return self.db.one("""
         SELECT sum(amount), count(amount)
           FROM current_tips
           JOIN participants p ON p.username = tipper
          WHERE tippee = %s
            AND p.claimed_time IS NOT null
            AND p.is_suspicious IS NOT true
            AND p.is_closed IS NOT true
            AND is_funded
            AND amount > 0
        """, (self.username,))


    def update_giving_and_teams(self):
        with self.db.get_cursor() as cursor:
            updated_giving = self.update_giving(cursor)
            for payment_instruction in updated_giving:
                Team.from_id(payment_instruction.team_id).update_receiving(cursor)


    def update_giving(self, cursor=None):
        # Update is_funded on payment_instructions
        has_credit_card = self.get_credit_card_error() == ''
        updated = (cursor or self.db).all("""
            UPDATE payment_instructions
               SET is_funded = %(has_credit_card)s
             WHERE participant_id = %(participant_id)s
               AND is_funded <> %(has_credit_card)s
         RETURNING *
        """, dict(participant_id=self.id, has_credit_card=has_credit_card))

        r = (cursor or self.db).one("""
        WITH pi AS (
            SELECT amount
              FROM current_payment_instructions cpi
              JOIN teams t ON t.id = cpi.team_id
             WHERE participant_id = %(participant_id)s
               AND amount > 0
               AND is_funded
               AND t.is_approved
        )
            UPDATE participants p
               SET giving = COALESCE((SELECT sum(amount) FROM pi), 0)
                 , ngiving_to = COALESCE((SELECT count(amount) FROM pi), 0)
             WHERE p.id=%(participant_id)s
         RETURNING giving, ngiving_to
        """, dict(participant_id=self.id))
        self.set_attributes(giving=r.giving, ngiving_to=r.ngiving_to)

        return updated

    def _update_due(self, team_id, id, cursor=None):
        """Transfer existing due value to newly inserted record
        """
        # Copy due to new record
        (cursor or self.db).run("""
            UPDATE payment_instructions p
               SET due = COALESCE((
                      SELECT due
                        FROM payment_instructions s
                       WHERE participant_id = %(participant_id)s
                         AND team_id = %(team_id)s
                         AND due > 0
                   ), 0)
             WHERE p.id = %(id)s
        """, dict(participant_id=self.id, team_id=team_id, id=id))

        # Reset older due values to 0
        self._reset_due(team_id, except_for=id, cursor=cursor)
        (cursor or self.db).run("""
            UPDATE payment_instructions p
               SET due = 0
             WHERE participant_id = %(participant_id)s
               AND team_id = %(team_id)s
               AND due > 0
               AND p.id != %(id)s
        """, dict(participant_id=self.id, team_id=team_id, id=id))

    def _reset_due(self, team_id, except_for=-1, cursor=None):
        (cursor or self.db).run("""
            UPDATE payment_instructions p
               SET due = 0
             WHERE participant_id = %(participant_id)s
               AND team_id = %(team_id)s
               AND due > 0
               AND p.id != %(id)s
        """, dict(participant_id=self.id, team_id=team_id, id=except_for))

    def update_taking(self, cursor=None):
        (cursor or self.db).run("""

            UPDATE participants
               SET taking=COALESCE((SELECT sum(receiving) FROM teams WHERE owner=%(username)s), 0)
                 , ntaking_from=COALESCE((SELECT count(*) FROM teams WHERE owner=%(username)s), 0)
             WHERE username=%(username)s

        """, dict(username=self.username))


    def update_is_free_rider(self, is_free_rider, cursor=None):
        with self.db.get_cursor(cursor) as cursor:
            cursor.run( "UPDATE participants SET is_free_rider=%(is_free_rider)s "
                        "WHERE username=%(username)s"
                      , dict(username=self.username, is_free_rider=is_free_rider)
                       )
            self.app.add_event( cursor
                              , 'participant'
                              , dict( id=self.id
                                    , action='set'
                                    , values=dict(is_free_rider=is_free_rider)
                                     )
                               )
            self.set_attributes(is_free_rider=is_free_rider)


    # Random Junk
    # ===========

    @property
    def profile_url(self):
        base_url = gratipay.base_url
        username = self.username
        return '{base_url}/{username}/'.format(**locals())


    def get_teams(self, only_approved=False, only_open=False, cursor=None):
        """Return a list of teams this user is an owner or member of.
        """
        teams = (cursor or self.db).all("""
            SELECT teams.*::teams FROM teams WHERE owner=%s

            UNION

            SELECT teams.*::teams FROM teams WHERE id IN (
                SELECT team_id FROM current_takes WHERE participant_id=%s
            )
        """, (self.username, self.id))

        if only_approved:
            teams = [t for t in teams if t.is_approved]
        if only_open:
            teams = [t for t in teams if not t.is_closed]
        return teams


    def member_of(self, team):
        """Given a Team object, return a boolean.
        """
        for take in team.get_current_takes():
            if take['participant'] == self:
                return True
        return False


    def insert_into_communities(self, is_member, name, slug):
        participant_id = self.id
        self.db.run("""

            INSERT INTO community_members
                        (ctime, name, slug, participant, is_member)
                 VALUES ( COALESCE (( SELECT ctime
                                        FROM community_members
                                       WHERE participant=%(participant_id)s
                                         AND slug=%(slug)s
                                       LIMIT 1
                                      ), CURRENT_TIMESTAMP)
                        , %(name)s, %(slug)s, %(participant_id)s, %(is_member)s
                         )

        """, locals())


    def change_username(self, suggested):
        """Raise Response or return None.

        Usernames are limited to alphanumeric characters, plus ".,-_:@ ",
        and can only be 32 characters long.

        """
        # TODO: reconsider allowing unicode usernames
        suggested = suggested and suggested.strip()

        if not suggested:
            raise UsernameIsEmpty(suggested)

        if len(suggested) > USERNAME_MAX_SIZE:
            raise UsernameTooLong(suggested)

        if set(suggested) - ASCII_ALLOWED_IN_USERNAME:
            raise UsernameContainsInvalidCharacters(suggested)

        lowercased = suggested.lower()

        # Don't allow any username which is the name of a
        # file existing on the web_root folder.
        for name in (lowercased, lowercased + '.spt'):
            if name in gratipay.RESTRICTED_USERNAMES:
                raise UsernameIsRestricted(suggested)

        if suggested != self.username:
            try:
                # Will raise IntegrityError if the desired username is taken.
                with self.db.get_cursor(back_as=tuple) as c:
                    self.app.add_event( c
                                      , 'participant'
                                      , dict( id=self.id
                                            , action='set'
                                            , values=dict(username=suggested)
                                             )
                                       )
                    actual = c.one( "UPDATE participants "
                                    "SET username=%s, username_lower=%s "
                                    "WHERE username=%s "
                                    "RETURNING username, username_lower"
                                   , (suggested, lowercased, self.username)
                                   )
            except IntegrityError:
                raise UsernameAlreadyTaken(suggested)

            assert (suggested, lowercased) == actual # sanity check
            self.set_attributes(username=suggested, username_lower=lowercased)

        return suggested


    def get_og_title(self):
        out = self.username
        giving = self.giving
        taking = self.taking
        if (giving > taking) and not self.anonymous_giving:
            out += " gives $%.2f/wk" % giving
        elif taking > 0:
            out += " takes $%.2f/wk" % taking
        else:
            out += " is"
        return out + " on Gratipay"


    def get_age_in_seconds(self):
        out = -1
        if self.claimed_time is not None:
            now = utcnow()
            out = (now - self.claimed_time).total_seconds()
        return out


    class StillOnATeam(Exception): pass
    class BalanceIsNotZero(Exception): pass

    def final_check(self, cursor, require_zero_balance=True):
        """Sanity-check that teams and balance have been dealt with.
        """
        if self.get_teams(cursor=cursor, only_open=True):
            raise self.StillOnATeam
        if require_zero_balance and self.balance != 0:
            raise self.BalanceIsNotZero

    def archive(self, cursor):
        """Given a cursor, use it to archive ourself.

        Archiving means changing to a random username so the username they were
        using is released. We also sign them out.

        """

        self.final_check(cursor)

        def reserve(cursor, username):
            check = cursor.one("""

                UPDATE participants
                   SET username=%s
                     , username_lower=%s
                     , claimed_time=NULL
                     , session_token=NULL
                     , session_expires=now()
                     , giving = 0
                     , taking = 0
                 WHERE username=%s
             RETURNING username

            """, ( username
                 , username.lower()
                 , self.username
                  ), default=NotSane)
            return check

        archived_as = safely_reserve_a_username(cursor, reserve=reserve)
        self.app.add_event(cursor, 'participant', dict( id=self.id
                                                      , action='archive'
                                                      , values=dict( new_username=archived_as
                                                                   , old_username=self.username
                                                                    )
                                                       ))
        return archived_as


    def take_over(self, account, have_confirmation=False):
        """Given an AccountElsewhere or a tuple (platform_name, user_id),
        associate an elsewhere account.

        Returns None or raises NeedConfirmation.

        This method associates an account on another platform (GitHub, Twitter,
        etc.) with the given Gratipay participant. Every account elsewhere has an
        associated Gratipay participant account, even if its only a stub
        participant.

        In certain circumstances, we want to present the user with a
        confirmation before proceeding to transfer the account elsewhere to
        the new Gratipay account; NeedConfirmation is the signal to request
        confirmation. If it was the last account elsewhere connected to the old
        Gratipay account, then we absorb the old Gratipay account into the new one,
        effectively archiving the old account.

        Here's what absorbing means:

            - consolidated tips to and fro are set up for the new participant

                Amounts are summed, so if alice tips bob $1 and carl $1, and
                then bob absorbs carl, then alice tips bob $2(!) and carl $0.

                And if bob tips alice $1 and carl tips alice $1, and then bob
                absorbs carl, then bob tips alice $2(!) and carl tips alice $0.

                The ctime of each new consolidated tip is the older of the two
                tips that are being consolidated.

                If alice tips bob $1, and alice absorbs bob, then alice tips
                bob $0.

                If alice tips bob $1, and bob absorbs alice, then alice tips
                bob $0.

            - all tips to and from the other participant are set to zero
            - the absorbed username is released for reuse
            - the absorption is recorded in an absorptions table

        This is done in one transaction.
        """

        if isinstance(account, AccountElsewhere):
            platform, user_id = account.platform, account.user_id
        else:
            platform, user_id = account

        CREATE_TEMP_TABLE_FOR_UNIQUE_TIPS = """

        CREATE TEMP TABLE __temp_unique_tips ON COMMIT drop AS

            -- Get all the latest tips from everyone to everyone.

            SELECT ctime, tipper, tippee, amount, is_funded
              FROM current_tips
             WHERE amount > 0;

        """

        CONSOLIDATE_TIPS_RECEIVING = """

            -- Create a new set of tips, one for each current tip *to* either
            -- the dead or the live account. If a user was tipping both the
            -- dead and the live account, then we create one new combined tip
            -- to the live account (via the GROUP BY and sum()).

            INSERT INTO tips (ctime, tipper, tippee, amount, is_funded)

                 SELECT min(ctime), tipper, %(live)s AS tippee, sum(amount), bool_and(is_funded)

                   FROM __temp_unique_tips

                  WHERE (tippee = %(dead)s OR tippee = %(live)s)
                        -- Include tips *to* either the dead or live account.

                AND NOT (tipper = %(dead)s OR tipper = %(live)s)
                        -- Don't include tips *from* the dead or live account,
                        -- lest we convert cross-tipping to self-tipping.

               GROUP BY tipper

        """

        CONSOLIDATE_TIPS_GIVING = """

            -- Create a new set of tips, one for each current tip *from* either
            -- the dead or the live account. If both the dead and the live
            -- account were tipping a given user, then we create one new
            -- combined tip from the live account (via the GROUP BY and sum()).

            INSERT INTO tips (ctime, tipper, tippee, amount)

                 SELECT min(ctime), %(live)s AS tipper, tippee, sum(amount)

                   FROM __temp_unique_tips

                  WHERE (tipper = %(dead)s OR tipper = %(live)s)
                        -- Include tips *from* either the dead or live account.

                AND NOT (tippee = %(dead)s OR tippee = %(live)s)
                        -- Don't include tips *to* the dead or live account,
                        -- lest we convert cross-tipping to self-tipping.

               GROUP BY tippee

        """

        ZERO_OUT_OLD_TIPS_RECEIVING = """

            INSERT INTO tips (ctime, tipper, tippee, amount)

                SELECT ctime, tipper, tippee, 0 AS amount
                  FROM __temp_unique_tips
                 WHERE tippee=%s

        """

        ZERO_OUT_OLD_TIPS_GIVING = """

            INSERT INTO tips (ctime, tipper, tippee, amount)

                SELECT ctime, tipper, tippee, 0 AS amount
                  FROM __temp_unique_tips
                 WHERE tipper=%s

        """

        TRANSFER_BALANCE_1 = """

            UPDATE participants
               SET balance = (balance - %(balance)s)
             WHERE username=%(dead)s
         RETURNING balance;

        """

        TRANSFER_BALANCE_2 = """

            INSERT INTO transfers (tipper, tippee, amount, context)
            SELECT %(dead)s, %(live)s, %(balance)s, 'take-over'
             WHERE %(balance)s > 0;

            UPDATE participants
               SET balance = (balance + %(balance)s)
             WHERE username=%(live)s
         RETURNING balance;

        """

        MERGE_EMAIL_ADDRESSES = """

            WITH emails_to_keep AS (
                     SELECT DISTINCT ON (address) id
                       FROM emails
                      WHERE participant_id IN (%(dead)s, %(live)s)
                   ORDER BY address, verification_end, verification_start DESC
                 )
            DELETE FROM emails
             WHERE participant_id IN (%(dead)s, %(live)s)
               AND id NOT IN (SELECT id FROM emails_to_keep);

            UPDATE emails
               SET participant_id = %(live)s
             WHERE participant_id = %(dead)s;

        """

        new_balance = None

        with self.db.get_cursor() as cursor:

            # Load the existing connection.
            # =============================
            # Every account elsewhere has at least a stub participant account
            # on Gratipay.

            elsewhere = cursor.one("""

                SELECT elsewhere.*::elsewhere_with_participant
                  FROM elsewhere
                  JOIN participants ON participant=participants.username
                 WHERE elsewhere.platform=%s AND elsewhere.user_id=%s

            """, (platform, user_id), default=NotSane)
            other = elsewhere.participant


            if self.username == other.username:
                # this is a no op - trying to take over itself
                return


            # Hard fail if the other participant has an identity.
            # ===================================================
            # Our identity system is very young. Maybe some day we'll do
            # something smarter here.

            if other.list_identity_metadata():
                raise WontTakeOverWithIdentities()


            # Make sure we have user confirmation if needed.
            # ==============================================
            # We need confirmation in whatever combination of the following
            # three cases:
            #
            #   - the other participant is not a stub; we are taking the
            #       account elsewhere away from another viable Gratipay
            #       participant
            #
            #   - the other participant has no other accounts elsewhere; taking
            #       away the account elsewhere will leave the other Gratipay
            #       participant without any means of logging in, and it will be
            #       archived and its tips absorbed by us
            #
            #   - we already have an account elsewhere connected from the given
            #       platform, and it will be handed off to a new stub
            #       participant

            # other_is_a_real_participant
            other_is_a_real_participant = other.is_claimed

            # this_is_others_last_login_account
            nelsewhere = len(other.get_elsewhere_logins(cursor))
            this_is_others_last_login_account = (nelsewhere <= 1)

            # we_already_have_that_kind_of_account
            nparticipants = cursor.one( "SELECT count(*) FROM elsewhere "
                                        "WHERE participant=%s AND platform=%s"
                                      , (self.username, platform)
                                       )
            assert nparticipants in (0, 1)  # sanity check
            we_already_have_that_kind_of_account = nparticipants == 1

            if elsewhere.is_team and we_already_have_that_kind_of_account:
                if len(self.get_accounts_elsewhere()) == 1:
                    raise TeamCantBeOnlyAuth

            need_confirmation = NeedConfirmation( other_is_a_real_participant
                                                , this_is_others_last_login_account
                                                , we_already_have_that_kind_of_account
                                                 )
            if need_confirmation and not have_confirmation:
                raise need_confirmation


            # We have user confirmation. Proceed.
            # ===================================
            # There is a race condition here. The last person to call this will
            # win. XXX: I'm not sure what will happen to the DB and UI for the
            # loser.


            # Move any old account out of the way.
            # ====================================

            if we_already_have_that_kind_of_account:
                new_stub_username = safely_reserve_a_username(cursor)
                cursor.run( "UPDATE elsewhere SET participant=%s "
                            "WHERE platform=%s AND participant=%s"
                          , (new_stub_username, platform, self.username)
                           )


            # Do the deal.
            # ============
            # If other_is_not_a_stub, then other will have the account
            # elsewhere taken away from them with this call.

            cursor.run( "UPDATE elsewhere SET participant=%s "
                        "WHERE platform=%s AND user_id=%s"
                      , (self.username, platform, user_id)
                       )


            # Fold the old participant into the new as appropriate.
            # =====================================================
            # We want to do this whether or not other is a stub participant.

            if this_is_others_last_login_account:

                other.clear_takes(cursor)

                # Take over tips.
                # ===============

                x, y = self.username, other.username
                cursor.run(CREATE_TEMP_TABLE_FOR_UNIQUE_TIPS)
                cursor.run(CONSOLIDATE_TIPS_RECEIVING, dict(live=x, dead=y))
                cursor.run(CONSOLIDATE_TIPS_GIVING, dict(live=x, dead=y))
                cursor.run(ZERO_OUT_OLD_TIPS_RECEIVING, (other.username,))
                cursor.run(ZERO_OUT_OLD_TIPS_GIVING, (other.username,))

                # Take over balance.
                # ==================

                other_balance = other.balance
                args = dict(live=x, dead=y, balance=other_balance)
                archive_balance = cursor.one(TRANSFER_BALANCE_1, args)
                other.set_attributes(balance=archive_balance)
                new_balance = cursor.one(TRANSFER_BALANCE_2, args)

                # Take over email addresses.
                # ==========================

                cursor.run(MERGE_EMAIL_ADDRESSES, dict(live=self.id, dead=other.id))

                # Take over payment routes.
                # =========================
                # Route ids logged in add_event call below, to keep the thread alive.

                route_ids = cursor.all( "UPDATE exchange_routes SET participant=%s "
                                        "WHERE participant=%s RETURNING id"
                                      , (self.id, other.id)
                                       )

                # Take over team ownership.
                # =========================

                cursor.run( "UPDATE teams SET owner=%s WHERE owner=%s"
                          , (self.username, other.username)
                           )

                # Disconnect any remaining elsewhere account.
                # ===========================================

                cursor.run("DELETE FROM elsewhere WHERE participant=%s", (y,))

                # Archive the old participant.
                # ============================
                # We always give them a new, random username. We sign out
                # the old participant.

                archive_username = other.archive(cursor)


                # Record the absorption.
                # ======================
                # This is for preservation of history.

                cursor.run( "INSERT INTO absorptions "
                            "(absorbed_was, absorbed_by, archived_as) "
                            "VALUES (%s, %s, %s)"
                          , ( other.username
                            , self.username
                            , archive_username
                             )
                           )

                self.app.add_event( cursor
                                  , 'participant'
                                  , dict( action='take-over'
                                        , id=self.id
                                        , values=dict( other_id=other.id
                                                     , exchange_routes=route_ids
                                                      )
                                         )
                                   )


        if new_balance is not None:
            self.set_attributes(balance=new_balance)

        self.update_avatar()

        # Note: the order ... doesn't actually matter here.
        self.update_taking()
        self.update_giving()

    def to_dict(self, details=False, inquirer=None):
        output = { 'id': self.id
                 , 'username': self.username
                 , 'avatar': self.avatar_url
                 , 'on': 'gratipay'
                  }

        if not details:
            return output

        # Key: taking
        # Values:
        #   3.00 - user takes this amount from teams
        output['taking'] = str(self.taking)
        output['ntaking_from'] = self.ntaking_from

        # Key: giving
        # Values:
        #   null - user is giving anonymously
        #   3.00 - user gives this amount
        if self.anonymous_giving:
            giving = None
        else:
            giving = str(self.giving)
        output['giving'] = giving
        output['ngiving_to'] = self.ngiving_to

        # Key: elsewhere
        accounts = self.get_accounts_elsewhere()
        elsewhere = output['elsewhere'] = {}
        for platform, account in accounts.items():
            fields = ['id', 'user_id', 'user_name']
            elsewhere[platform] = {k: getattr(account, k, None) for k in fields}

        return output


class NeedConfirmation(Exception):
    """Represent the case where we need user confirmation during a merge.

    This is used in the workflow for merging one participant into another.

    """

    def __init__(self, a, b, c):
        self.other_is_a_real_participant = a
        self.this_is_others_last_login_account = b
        self.we_already_have_that_kind_of_account = c
        self._all = (a, b, c)

    def __repr__(self):
        return "<NeedConfirmation: %r %r %r>" % self._all
    __str__ = __repr__

    def __eq__(self, other):
        return self._all == other._all

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        # bool(need_confirmation)
        A, B, C = self._all
        return A or C

class LastElsewhere(Exception): pass

class NonexistingElsewhere(Exception): pass

class TeamCantBeOnlyAuth(Exception): pass

class WontTakeOverWithIdentities(Exception): pass
