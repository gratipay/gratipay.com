from aspen import Response


_requesting_asset = lambda r: r.path.raw.startswith('/assets/')


def only_allow_certain_methods(request):
    method = request.method.upper()
    whitelist = ('GET', 'HEAD') if _requesting_asset(request) else ('GET', 'HEAD', 'POST')
    # POSTing to /assets/ interferes with the csrf.* functions if we're not careful
    if method not in whitelist:
        raise Response(405)


def add_headers_to_response(response):
    """Add security headers.
    """

    # http://en.wikipedia.org/wiki/Clickjacking#X-Frame-Options
    if 'X-Frame-Options' not in response.headers:
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    elif response.headers['X-Frame-Options'] == 'ALLOWALL':

        # ALLOWALL is non-standard. It's useful as a signal from a simplate
        # that it doesn't want X-Frame-Options set at all, but because it's
        # non-standard we don't send it. Instead we unset the header entirely,
        # which has the desired effect of allowing framing indiscriminately.
        #
        # Refs.:
        #
        #   http://en.wikipedia.org/wiki/Clickjacking#X-Frame-Options
        #   http://ipsec.pl/node/1094

        del response.headers['X-Frame-Options']

    # https://www.owasp.org/index.php/List_of_useful_HTTP_headers
    if 'X-Content-Type-Options' not in response.headers:
        response.headers['X-Content-Type-Options'] = 'nosniff'

    # https://www.owasp.org/index.php/List_of_useful_HTTP_headers
    if 'X-XSS-Protection' not in response.headers:
        response.headers['X-XSS-Protection'] = '1; mode=block'

    # https://www.w3.org/TR/referrer-policy/
    if 'Referrer-Policy' not in response.headers:
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
    if 'content-security-policy-report-only' not in response.headers:
        response.headers['content-security-policy-report-only'] = (
            "default-src 'self';"
            "script-src 'self' assets.gratipay.com 'unsafe-inline';"
            "style-src 'self' assets.gratipay.com downloads.gratipay.com cloud.typography.com;"
            "img-src *;"
            "font-src 'self' assets.gratipay.com cloud.typography.com data:;"
            "upgrade-insecure-requests;"
            "block-all-mixed-content;"
            "reflected-xss block;"
            "report-uri https://gratipay.report-uri.io/r/default/csp/reportOnly;"
        )
