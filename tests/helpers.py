"""
Helpers for the tests
"""

def raises(exception, func, string=None):
    try:
        a = func()
    except exception as e:
        if string:
            assert string in e.args[0]
        return True
    raise Exception("did not raise, gave %s" % a)
