"""
    Exceptions
    ~~~~~~~~~~~~
"""
class UnauthorizedTransactionError(Exception):
    """
    Raised when client tries to act on an unauthorized transaction.
    """
    pass

class NotConfiguredError(Exception):
    """
    Raised when client tries to make a call without configuring key and password.
    """
    pass
