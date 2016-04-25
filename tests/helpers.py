"""
Helpers for the tests
"""
import subprocess
import sys
import os
import re
import json

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

from contextlib import contextmanager

import conda.cli as cli
from conda.compat import StringIO


def raises(exception, func, string=None):
    try:
        a = func()
    except exception as e:
        if string:
            assert string in e.args[0]
        print(e)
        return True
    raise Exception("did not raise, gave %s" % a)


def run_conda_command(*args):
    env = os.environ.copy()
    p = subprocess.Popen((sys.executable, "-m", "conda") + args, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)

    stdout, stderr = [stream.strip().decode('utf-8').replace('\r\n', '\n').replace('\\\\', '\\')
                      for stream in p.communicate()]
    return stdout, stderr


class CapturedText(object):
    pass


@contextmanager
def captured(disallow_stderr=True):
    """
    Context manager to capture the printed output of the code in the with block

    Bind the context manager to a variable using `as` and the result will be
    in the stdout property.

    >>> from tests.helpers import capture
    >>> with captured() as c:
    ...     print('hello world!')
    ...
    >>> c.stdout
    'hello world!\n'
    """
    import sys

    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = outfile = StringIO()
    sys.stderr = errfile = StringIO()
    c = CapturedText()
    yield c
    c.stdout = outfile.getvalue()
    c.stderr = errfile.getvalue()
    sys.stdout = stdout
    sys.stderr = stderr
    if disallow_stderr and c.stderr:
        raise Exception("Got stderr output: %s" % c.stderr)


def capture_with_argv(*argv):
    sys.argv = argv
    stdout, stderr = StringIO(), StringIO()
    oldstdout, oldstderr = sys.stdout, sys.stderr
    sys.stdout = stdout
    sys.stderr = stderr
    try:
        cli.main()
    except SystemExit:
        pass
    sys.stdout = oldstdout
    sys.stderr = oldstderr

    stdout.seek(0)
    stderr.seek(0)
    stdout, stderr = stdout.read(), stderr.read()

    print('>>>>>>>>> stdout >>>>>>>>>')
    print(stdout)
    print('>>>>>>>>> stderr >>>>>>>>>')
    print(stderr)
    print('>>>>>>>>>')
    return stdout, stderr


def capture_json_with_argv(*argv, **kwargs):
    stdout, stderr = capture_with_argv(*argv)

    if kwargs.get('relaxed'):
        match = re.match('\A.*?({.*})', stdout, re.DOTALL)
        if match:
            stdout = match.groups()[0]
    elif stderr:
        # TODO should be exception
        return stderr

    try:
        return json.loads(stdout)
    except ValueError:
        print(str(stdout), str(stderr))
        raise


def assert_equals(a, b, output=""):
    output = "%r != %r" % (a.lower(), b.lower()) + "\n\n" + output
    assert a.lower() == b.lower(), output


def assert_not_in(a, b, output=""):
    assert a.lower() not in b.lower(), "%s %r should not be found in %r" % (output, a.lower(), b.lower())


def assert_in(a, b, output=""):
    assert a.lower() in b.lower(), "%s %r cannot be found in %r" % (output, a.lower(), b.lower())
