"""
Helpers for the tests
"""
from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
import json
import os
from os.path import dirname, join, abspath
import re
from shlex import split
from conda._vendor.auxlib.compat import shlex_split_unicode
import sys
from tempfile import gettempdir
from uuid import uuid4

from conda import cli
from conda._vendor.auxlib.decorators import memoize
from conda.base.context import context, reset_context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import iteritems, itervalues, encode_arguments
from conda.common.io import argv, captured, captured as common_io_captured, env_var
from conda.core.subdir_data import SubdirData, make_feature_record
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import lexists
from conda.gateways.logging import initialize_logging
from conda.models.channel import Channel
from conda.models.records import PackageRecord
from conda.resolve import Resolve

from functools import partial
import pytest

try:
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    import mock
    from mock import patch

TEST_DATA_DIR = abspath(join(dirname(__file__), "..", "test_data"))

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


def capture_json_with_argv(command, disallow_stderr=True, ignore_stderr=False, **kwargs):
    stdout, stderr, exit_code = run_inprocess_conda_command(command, disallow_stderr)
    if kwargs.get('relaxed'):
        match = re.match(r'\A.*?({.*})', stdout, re.DOTALL)
        if match:
            stdout = match.groups()[0]
    elif stderr and not ignore_stderr:
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


def run_inprocess_conda_command(command, disallow_stderr=True):
    # anything that uses this function is an integration test
    reset_context(())
    # May want to do this to command:
    with argv(encode_arguments(shlex_split_unicode(command))), captured(disallow_stderr) as c:
        initialize_logging()
        try:
            exit_code = cli.main(*sys.argv)
        except SystemExit:
            pass
    print(c.stderr, file=sys.stderr)
    print(c.stdout)
    return c.stdout, c.stderr, exit_code


def add_subdir(dist_string):
    channel_str, package_str = dist_string.split('::')
    channel_str = channel_str + '/' +  context.subdir
    return '::'.join([channel_str, package_str])


def add_subdir_to_iter(iterable):
    if isinstance(iterable, dict):
        return {add_subdir(k) : v for k, v in iterable.items()}
    elif isinstance(iterable, list):
        return list(map(add_subdir, iterable))
    elif isinstance(iterable, set):
        return set(map(add_subdir, iterable))
    elif isinstance(iterable, tuple):
        return tuple(map(add_subdir, iterable))
    else:
        raise Exception("Unable to add subdir to object of unknown type.")


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
        index[rec] = rec


def add_feature_records_legacy(index):
    all_features = set()
    for rec in itervalues(index):
        if rec.track_features:
            all_features.update(rec.track_features)

    for feature_name in all_features:
        rec = make_feature_record(feature_name)
        index[rec] = rec

@memoize
def get_index_r_1(subdir=context.subdir):
    with open(join(dirname(__file__), 'data', 'index.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-1/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}
    add_feature_records_legacy(index)
    r = Resolve(index, channels=(channel,))
    return index, r


@memoize
def get_index_r_2(subdir=context.subdir):
    with open(join(dirname(__file__), 'data', 'index2.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-2/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))
    return index, r


@memoize
def get_index_r_4(subdir=context.subdir):
    with open(join(dirname(__file__), 'data', 'index4.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-4/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))

    return index, r


@memoize
def get_index_r_5(subdir=context.subdir):
    with open(join(dirname(__file__), 'data', 'index5.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-5/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "true", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))

    return index, r


@memoize
def get_index_must_unfreeze(subdir=context.subdir):
    repodata = {
        "info": {
            "subdir": subdir,
            "arch": context.arch_name,
            "platform": context.platform,
        },
        "packages": {
            "foobar-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [
                    "libbar 2.0.*",
                    "libfoo 1.0.*"
                ],
                "md5": "11ec1194bcc56b9a53c127142a272772",
                "name": "foobar",
                "timestamp": 1562861325613,
                "version": "1.0"
            },
            "foobar-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [
                    "libbar 2.0.*",
                    "libfoo 2.0.*"
                ],
                "md5": "f8eb5a7fa1ff6dead4e360631a6cd048",
                "name": "foobar",
                "version": "2.0"
            },

            "libbar-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "f51f4d48a541b7105b5e343704114f0f",
                "name": "libbar",
                "timestamp": 1562858881022,
                "version": "1.0"
            },
            "libbar-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "27f4e717ed263f909074f64d9cbf935d",
                "name": "libbar",
                "timestamp": 1562858881748,
                "version": "2.0"
            },

            "libfoo-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "ad7c088566ffe2389958daedf8ff312c",
                "name": "libfoo",
                "timestamp": 1562858763881,
                "version": "1.0"
            },
            "libfoo-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "daf7af7086d8f22be49ae11bdc41f332",
                "name": "libfoo",
                "timestamp": 1562858836924,
                "version": "2.0"
            },

            "qux-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [
                    "libbar 2.0.*",
                    "libfoo 1.0.*"
                ],
                "md5": "18604cbe4f789fe853232eef4babd4f9",
                "name": "qux",
                "timestamp": 1562861393808,
                "version": "1.0"
            },
            "qux-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [
                    "libbar 1.0.*",
                    "libfoo 2.0.*"
                ],
                "md5": "892aa4b9ec64b67045a46866ef1ea488",
                "name": "qux",
                "timestamp": 1562861394828,
                "version": "2.0"
            }
        }
    }
    channel = Channel('https://conda.anaconda.org/channel-freeze/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}
    r = Resolve(index, channels=(channel,))

    return index, r


# Do not memoize this get_index to allow different CUDA versions to be detected
def get_index_cuda(subdir=context.subdir):
    with open(join(dirname(__file__), 'data', 'index.json')) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel('https://conda.anaconda.org/channel-1/%s' % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd._package_records}

    add_feature_records_legacy(index)
    r = Resolve(index, channels=(channel,))
    return index, r
