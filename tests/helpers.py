"""
Helpers for the tests
"""
import subprocess
import os

def raises(exception, func, string=None):
    try:
        a = func()
    except exception as e:
        if string:
            assert string in e.args[0]
        return True
    raise Exception("did not raise, gave %s" % a)

def run_in(command, shell='bash'):
    env = {}
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(__file__))
    p = subprocess.Popen([shell, '-c', command], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env)
    stdout, stderr = p.communicate()
    return (stdout.decode('utf-8').replace('\r\n', '\n'),
        stderr.decode('utf-8').replace('\r\n', '\n'))
