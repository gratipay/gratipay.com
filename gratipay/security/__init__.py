from aspen import Response


def only_allow_certain_methods(request):
    whitelisted = ['GET', 'HEAD', 'POST']
    if request.method.upper() not in whitelisted:
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
