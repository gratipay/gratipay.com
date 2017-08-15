"""
This module contains exceptions shared across application code.
"""

from __future__ import print_function, unicode_literals

from gratipay.utils.i18n import LocalizedErrorResponse


class ProblemChangingUsername(Exception):
    def __str__(self):
        return self.msg.format(self.args[0])

class UsernameIsEmpty(ProblemChangingUsername):
    msg = "You need to provide a username!"

class UsernameTooLong(ProblemChangingUsername):
    msg = "The username '{}' is too long."

class UsernameContainsInvalidCharacters(ProblemChangingUsername):
    msg = "The username '{}' contains invalid characters."

class UsernameIsRestricted(ProblemChangingUsername):
    msg = "The username '{}' is restricted."

class UsernameAlreadyTaken(ProblemChangingUsername):
    msg = "The username '{}' is already taken."


class ProblemChangingEmail(LocalizedErrorResponse):
    pass

class EmailAlreadyVerified(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("You have already added and verified that address.")

class EmailTaken(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("That address is already linked to a different Gratipay account.")

class CannotRemovePrimaryEmail(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("You cannot remove your primary email address.")

class EmailNotOnFile(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("That email address is not on file for this package.")

class EmailNotVerified(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("That email address is not verified.")

class TooManyEmailAddresses(ProblemChangingEmail):
    def lazy_body(self, _):
        return _("You've reached the maximum number of email addresses we allow.")


class NoEmailAddress(Exception):
    pass

class Throttled(LocalizedErrorResponse):
    def lazy_body(self, _):
        return _("You've initiated too many emails too quickly. Please try again in a minute or two.")


class ProblemChangingNumber(Exception):
    def __str__(self):
        return self.msg


class NotSane(Exception):
    """This is used when a sanity check fails.

    A sanity check is when it really seems like the logic shouldn't allow the
    condition to arise, but you never know.

    """


class TooGreedy(Exception): pass
class NoSelfTipping(Exception): pass
class NoTippee(Exception): pass
class BadAmount(Exception): pass
class InvalidTeamName(Exception): pass

class FailedToReserveUsername(Exception): pass

class NegativeBalance(Exception):
    def __str__(self):
        return "Negative balance not allowed in this context."

class NotWhitelisted(Exception): pass
class NoPackages(Exception): pass
class NoTeams(Exception): pass
