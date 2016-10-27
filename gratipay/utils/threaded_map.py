from __future__ import absolute_import, division, print_function, unicode_literals

from multiprocessing.dummy import Pool as ThreadPool


class ExceptionWrapped(Exception):
    pass


def threaded_map(func, iterable, threads=5):
    pool = ThreadPool(threads)
    def g(*a, **kw):
        # Without this wrapper we get a traceback from inside multiprocessing.
        try:
            return func(*a, **kw)
        except Exception as e:
            import traceback
            raise ExceptionWrapped(e, traceback.format_exc())
    try:
        r = pool.map(g, iterable)
    except ExceptionWrapped as e:
        print(e.args[1])
        raise e.args[0]
    pool.close()
    pool.join()
    return r
