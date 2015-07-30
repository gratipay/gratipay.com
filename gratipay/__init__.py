"""This is the Python library behind gratipay.com.
"""
import datetime
import locale
from decimal import Decimal


try:  # XXX This can't be right.
    locale.setlocale(locale.LC_ALL, "en_US.utf8")
except locale.Error:
    import sys
    if sys.platform == 'win32':
        locale.setlocale(locale.LC_ALL, '')
    else:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


BIRTHDAY = datetime.date(2012, 6, 1)
CARDINALS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
             'eight', 'nine']
ORDINALS = ['zeroth', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth',
            'seventh', 'eighth', 'ninth', 'tenth']
MONTHS = [None, 'January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

def age():
    today = datetime.date.today()
    nmonths = (12 - BIRTHDAY.month) \
            + (12 * (today.year - BIRTHDAY.year - 1)) \
            + (today.month)
    plural = 's' if nmonths != 1 else ''
    if nmonths < 10:
        nmonths = CARDINALS[nmonths]
    else:
        nmonths = str(nmonths)
    return "%s month%s" % (nmonths, plural)


class NotSane(Exception):
    """This is used when a sanity check fails.

    A sanity check is when it really seems like the logic shouldn't allow the
    condition to arise, but you never know.

    """

db = None # This global is wired in wireup. It's an instance of
          # gratipay.postgres.PostgresManager.


MAX_TIP = MAX_PAYMENT = Decimal('1000.00')
MIN_TIP = MIN_PAYMENT = Decimal('0.00')

RESTRICTED_IDS = None


def set_version_header(response, website):
    response.headers['X-Gratipay-Version'] = website.version
