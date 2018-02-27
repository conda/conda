"""
Helpers for the tests
"""
from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
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
from conda.common.compat import iteritems, itervalues
from conda.common.io import argv, captured, captured as common_io_captured, env_var
from conda.core.subdir_data import SubdirData, make_feature_record
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import lexists
from conda.gateways.logging import initialize_logging
from conda.models.channel import Channel
from conda.models.dist import Dist
from conda.models.records import PackageRecord
from conda.resolve import Resolve

try:
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    import mock
    from mock import patch

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


@contextmanager
def captured(disallow_stderr=True):
    # same as common.io.captured but raises Exception if unexpected output was written to stderr
    try:
        with common_io_captured() as c:
            yield c
    finally:
        c.stderr = strip_expected(c.stderr)
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
    with argv(split(command)), captured() as c:
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
        rec = PackageRecord.from_objects(info,
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


def add_feature_records_legacy(index):
    all_features = set()
    for rec in itervalues(index):
        if rec.track_features:
            all_features.update(rec.track_features)

    for feature_name in all_features:
        rec = make_feature_record(feature_name)
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

    channel = Channel('https://conda.anaconda.org/channel-1/%s' % context.subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {Dist(prec): prec for prec in sd._package_records}
    add_feature_records_legacy(index)
    r = Resolve(index, channels=(channel,))
    return index, r


@memoize
def get_index_r_2():
    with open(join(dirname(__file__), 'index2.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": context.subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-2/%s' % context.subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {Dist(prec): prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))
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

    channel = Channel('https://conda.anaconda.org/channel-3/%s' % context.subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {Dist(prec): prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))
    return index, r


@memoize
def get_index_r_4():
    with open(join(dirname(__file__), 'index4.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": context.subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-4/%s' % context.subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {Dist(prec): prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))

    return index, r


@memoize
def get_index_r_5():
    with open(join(dirname(__file__), 'index5.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": context.subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-5/%s' % context.subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "true", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {Dist(prec): prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))

    return index, r
