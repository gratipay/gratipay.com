import htmlmin
import csscompressor
from jsmin import jsmin
import xmlformatter


def minify_output(response, website):
    if response.headers.get('Content-Type', '').startswith('text/css'):
        response.body = csscompressor.compress(response.body)
