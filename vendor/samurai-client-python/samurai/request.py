"""
    Python restful client.
    ~~~~~~~~~~~~~~~~~~~~~~
"""
import urllib2
import base64

import config
from errors import NotConfiguredError

class Request(urllib2.Request):
    """
    `urllib2.Request` doesn't support PUT and DELETE.
    Augmenting it to support whole REST spectrum.
    """
    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False, method=None):
       if data:
          headers['Content-Type'] = 'text/xml'
       urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
       self.method = method and method.upper() or None

    def get_method(self):
        if self.method:
            return self.method

        return urllib2.Request.get_method(self)

def fetch_url(req,
              merchant_key=config.merchant_key,
              merchant_password=config.merchant_password):
    """
    Opens a request to `req`. Handles basic auth with given `merchant_key`
    and `merchant_password`.
    """
    # Check if user configured `key` and `password`
    if not merchant_key or not merchant_password:
        raise NotConfiguredError('Please set merchant_key and merchant_password before making the call.')
    auth_info = base64.encodestring('%s:%s' % (merchant_key, merchant_password)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % auth_info)
    opener = urllib2.build_opener()
    try:
        res = opener.open(req).read()
    except urllib2.URLError, ex:
        # If the server returned an error, return it.
        # Else if there is a network problem, let the client handle it.
        if getattr(ex, 'read', None):
            res = ex.read()
        else:
            raise ex
    if config.debug:
        dump_request(req, res)
    return res

def dump_request(req, res, logger=config.logger):
    """
    Logs `req` and `res` using `logger`.
    """
    logger.debug("Request url: %s %s\nRequest data: %s\nResult: %s\n" % (req.get_method(), req.get_full_url(),
                                                                        req.get_data(),
                                                                        res))
