"""
Helpers for the tests
"""
from __future__ import print_function, division, absolute_import

import subprocess
import sys
import os
import re
import json
from shlex import split

from conda.base.context import reset_context
from conda.common.io import captured, argv, replace_log_streams
from conda.gateways.logging import initialize_logging
from conda import cli

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

from contextlib import contextmanager

from conda.common.compat import StringIO, iteritems

expected_error_prefix = 'Using Anaconda Cloud api site https://api.anaconda.org'
def strip_expected(stderr):
    if expected_error_prefix and stderr.startswith(expected_error_prefix):
        stderr = stderr[len(expected_error_prefix):].lstrip()
    return stderr

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
    # used in tests_config (31 times) and test_info (6 times)
    # anything that uses this function is an integration test
    env = {str(k): str(v) for k, v in iteritems(os.environ)}
    p = subprocess.Popen((sys.executable, "-m", "conda") + args, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)

    stdout, stderr = [stream.strip()
                          .decode('utf-8')
                          .replace('\r\n', '\n')
                          .replace('\\\\', '\\')
                          .replace("Using Anaconda API: https://api.anaconda.org\n", "")
                      for stream in p.communicate()]
    print(stdout)
    print(stderr, file=sys.stderr)
    # assert p.returncode == 0, p.returncode
    if args[0] == 'config':
        reset_context([args[2]])
    return stdout, strip_expected(stderr)


class CapturedText(object):
    pass


@contextmanager
def captured(disallow_stderr=True):
    # """
    # Context manager to capture the printed output of the code in the with block
    #
    # Bind the context manager to a variable using `as` and the result will be
    # in the stdout property.
    #
    # >>> from tests.helpers import captured
    # >>> with captured() as c:
    # ...     print('hello world!')
    # ...
    # >>> c.stdout
    # 'hello world!\n'
    # """
    import sys

    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = outfile = StringIO()
    sys.stderr = errfile = StringIO()
    c = CapturedText()
    try:
        yield c
    finally:
        c.stdout = outfile.getvalue()
        c.stderr = strip_expected(errfile.getvalue())
        sys.stdout = stdout
        sys.stderr = stderr
        if disallow_stderr and c.stderr:
            raise Exception("Got stderr output: %s" % c.stderr)


def capture_json_with_argv(command, **kwargs):
    # used in test_config (6 times), test_info (2 times), test_list (5 times), and test_search (10 times)
    # anything that uses this function is an integration test
    stdout, stderr, exit_code = run_inprocess_conda_command(command)
    if kwargs.get('relaxed'):
        match = re.match('\A.*?({.*})', stdout, re.DOTALL)
        if match:
            stdout = match.groups()[0]
    elif stderr:
        # TODO should be exception
        return stderr
    try:
        return json.loads(stdout.strip())
    except ValueError:
        raise


def assert_equals(a, b, output=""):
    output = "%r != %r" % (a.lower(), b.lower()) + "\n\n" + output
    assert a.lower() == b.lower(), output


def assert_not_in(a, b, output=""):
    assert a.lower() not in b.lower(), "%s %r should not be found in %r" % (output, a.lower(), b.lower())


def assert_in(a, b, output=""):
    assert a.lower() in b.lower(), "%s %r cannot be found in %r" % (output, a.lower(), b.lower())


def run_inprocess_conda_command(command):
    # anything that uses this function is an integration test
    reset_context(())
    with argv(split(command)), captured() as c, replace_log_streams():
        initialize_logging()
        try:
            exit_code = cli.main()
        except SystemExit:
            pass
    print(c.stderr, file=sys.stderr)
    print(c.stdout)
    return c.stdout, c.stderr, exit_code
