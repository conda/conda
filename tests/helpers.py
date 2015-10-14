"""
Helpers for the tests
"""
import subprocess
import sys
import os
import json

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None
import tempfile

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

def run_in(command, shell='bash'):
    if shell == 'cmd.exe':
        cmd_script = tempfile.NamedTemporaryFile(suffix='.bat', mode='wt', delete=False)
        cmd_script.write(command)
        cmd_script.close()
        p = subprocess.Popen([shell, '/d', '/c', cmd_script.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        os.unlink(cmd_script.name)
    else:
        p = subprocess.Popen([shell, '-c', command], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    return (stdout.decode('utf-8').replace('\r\n', '\n'),
        stderr.decode('utf-8').replace('\r\n', '\n'))

python = sys.executable
conda = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'conda')

def run_conda_command(*args):
    env = os.environ.copy()
    # Make sure bin/conda imports *this* conda.
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(__file__))
    env['CONDARC'] = ' '
    p= subprocess.Popen((python, conda,) + args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env)
    stdout, stderr = p.communicate()
    return (stdout.decode('utf-8').replace('\r\n', '\n'),
        stderr.decode('utf-8').replace('\r\n', '\n'))

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
    return stdout.read(), stderr.read()


def capture_json_with_argv(*argv):
    stdout, stderr = capture_with_argv(*argv)
    if stderr:
        # TODO should be exception
        return stderr

    try:
        return json.loads(stdout)
    except ValueError:
        print(stdout, stderr)
        raise
