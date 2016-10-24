from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import time
import ijson.backends.yajl2_cffi as ijson
from collections import OrderedDict


path = sys.argv[1]
parser = ijson.parse(open(path))
log = lambda *a: print(*a, file=sys.stderr)


def emit(package, emails):
    """Takes a package and returns a serialization suitable for COPY.
    """
    if not package or package['name'].startswith('_'):
        log('skipping', package)
        return 0

    package['emails'] = emails
    out = []
    for k,v in package.iteritems():
        if type(v) is unicode:
            v = v.encode('utf8')
        else:
            v = str(v)
        out.append(v)
    print(b'\t'.join(out))
    return 1


def main():
    start = time.time()
    package = emails = None
    nprocessed = 0

    def log_stats():
        log("processed {} packages in {:3.0f} seconds"
            .format(nprocessed, time.time() - start))

    for prefix, event, value in parser:

        prefix = prefix.decode('utf8')
        if type(value) is str:
            value = value.decode('utf8')

        if not prefix and event == 'map_key':

            # Flush the previous package. We count on the first package being garbage.
            processed = emit(package, emails)
            nprocessed += processed
            if processed and not(nprocessed % 1000):
                log_stats()

            # Start a new package.
            package = OrderedDict({'name': value})
            emails = []

        key = lambda k: package['name'] + '.' + k

        if event == 'string':
            if prefix == key('description'):
                package['description'] = value
            elif prefix == key('license'):
                package['license'] = value
            elif prefix == key('time.modified'):
                package['mtime'] = value
            elif prefix in (key('author.item.email'), key('maintainers.item.email')):
                emails.append(value)

    log_stats()


if __name__ == '__main__':
    main()
