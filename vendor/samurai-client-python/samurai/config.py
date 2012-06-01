"""
    Configs for Samurai API.
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Set samurai api configurations on this module.

    Import this module and set the `merchant_key` and `merchant_password`.
    Other modules use the configuration set on this object.
    ::
        import samurai.config as config
        config.merchant_key = your_merchant_key
        config.merchant_password = your_merchant_password
        config.processor_token = default processor token
"""
import sys
import logging
from logging import Formatter, StreamHandler

debug = False
# FIXME: Leaving it here for dev. To be removed.
merchant_key = 'a1ebafb6da5238fb8a3ac9f6'
merchant_password = 'ae1aa640f6b735c4730fbb56'
processor_token = '5a0e1ca1e5a11a2997bbf912'

top_uri='https://api.samurai.feefighters.com/v1/',

log_format = '%(levelname)s - %(asctime)s - %(filename)s:%(funcName)s:%(lineno)s - \n%(message)s\n\n'
def default_logger():
    """
    Returns an instance of default logger.
    Default logger dumps data to `sys.stderr`.
    """
    logger = logging.getLogger('samurai')
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stderr)
    handler.setFormatter(Formatter(log_format))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = default_logger()
