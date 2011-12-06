"""
    General utilities
    ~~~~~~~~~~~~~~~~~~
"""
import datetime

def pipe(cur_val, *fns):
    """
    Pipes `cur_val` through `fns`.
    ::
        def sqr(x): return x * x

        def negate(x): return -x

        `pipe(5, sqr, negate)`

    is the same as
    ::
        negate(sqr(5))
    """
    for fn in fns:
        cur_val = fn(cur_val)
    return cur_val

def str_to_datetime(date_str):
    try:
        val = datetime.datetime.strptime(date_str,  "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        val = date_str
    return val

def str_to_boolean(bool_str):
    if bool_str.lower() != 'false' and bool(bool_str):
        return True
    return False
