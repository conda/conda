"""
Helpers for the tests
"""
from __future__ import absolute_import, division, print_function

from collections import defaultdict
import json
import os
from os.path import dirname, join
import re
from shlex import split
import sys
from tempfile import gettempdir
from uuid import uuid4

from conda import cli
from conda._vendor.auxlib.decorators import memoize
from conda.base.context import context, reset_context
from conda.common.io import argv, captured, replace_log_streams
from conda.core.repodata import make_feature_record
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import lexists
from conda.gateways.logging import initialize_logging
from conda.models.channel import Channel
from conda.models.dist import Dist
from conda.models.index_record import IndexRecord
from conda.resolve import Resolve

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

from contextlib import contextmanager

from conda.common.compat import StringIO, iteritems, itervalues

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


@contextmanager
def tempdir():
    tempdirdir = gettempdir()
    dirname = str(uuid4())[:8]
    prefix = join(tempdirdir, dirname)
    try:
        os.makedirs(prefix)
        yield prefix
    finally:
        if lexists(prefix):
            rm_rf(prefix)


def supplement_index_with_repodata(index, repodata, channel, priority):
    repodata_info = repodata['info']
    arch = repodata_info.get('arch')
    platform = repodata_info.get('platform')
    subdir = repodata_info.get('subdir')
    if not subdir:
        subdir = "%s-%s" % (repodata_info['platform'], repodata_info['arch'])
    auth = channel.auth
    for fn, info in iteritems(repodata['packages']):
        rec = IndexRecord.from_objects(info,
                                       fn=fn,
                                       arch=arch,
                                       platform=platform,
                                       channel=channel,
                                       subdir=subdir,
                                       # schannel=schannel,
                                       priority=priority,
                                       # url=join_url(channel_url, fn),
                                       auth=auth)
        dist = Dist(rec)
        index[dist] = rec


def add_feature_records(index):
    all_features = defaultdict(set)
    # for rec in itervalues(index):
    #     for k, v in iteritems(rec.requires_features):
    #         all_features[k].add(v)
    #     for k, v in iteritems(rec.provides_features):
    #         all_features[k].add(v)

    for feature_name, feature_values in iteritems(all_features):
        for feature_value in feature_values:
            rec = make_feature_record(feature_name, feature_value)
            index[Dist(rec)] = rec


@memoize
def get_index_r_1():
    with open(join(dirname(__file__), 'index.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": context.subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    # channel = Channel('https://conda.anaconda.org/channel-1/%s' % context.subdir)
    # sd = SubdirData(channel)
    # with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
    #     sd._process_raw_repodata_str(json.dumps(repodata))
    # sd._loaded = True
    # SubdirData._cache_[channel.url(with_credentials=True)] = sd

    channel='https://repo.continuum.io/pkgs/free'
    schannel='defaults'
    subdir = context.subdir
    precs = (IndexRecord.from_objects(
        prec, channel=channel, schannel=schannel, fn=fn, subdir=subdir,
        url='%s/%s/%s' % (channel, subdir, fn),
        priority=2,
    ) for fn, prec in iteritems(repodata['packages']))
    index = {Dist(prec): prec for prec in precs}
    add_feature_records(index)
    # r = Resolve(index, channels=(channel,))
    r = Resolve(index)
    return index, r


@memoize
def get_index_r_3():
    with open(join(dirname(__file__), 'index3.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": context.subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    # channel = Channel('https://conda.anaconda.org/channel-1/%s' % context.subdir)
    # sd = SubdirData(channel)
    # with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
    #     sd._process_raw_repodata_str(json.dumps(repodata))
    # sd._loaded = True
    # SubdirData._cache_[channel.url(with_credentials=True)] = sd

    channel='https://conda.anaconda.org/conda-test'
    schannel='conda-test'
    subdir = context.subdir
    precs = (IndexRecord.from_objects(
        prec, channel=channel, schannel=schannel, fn=fn, subdir=subdir,
        url='%s/%s/%s' % (channel, subdir, fn),
        priority=4
    ) for fn, prec in iteritems(repodata['packages']))
    index = {Dist(prec): prec for prec in precs}
    add_feature_records(index)
    # r = Resolve(index, channels=(channel,))
    r = Resolve(index)
    return index, r
