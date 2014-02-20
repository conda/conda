"""
Helpers for the tests
"""

def _raises(exception, func):
    try:
        a = func()
    except exception:
        return True
    raise Exception("did not raise, gave %s" % a)
