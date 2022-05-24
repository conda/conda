# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from collections import defaultdict, namedtuple
from contextlib import contextmanager
from functools import partial
import os
from os.path import join
import random
import unittest

import pytest

from conda import CondaError
from conda.base.context import context, stack_context, conda_tests_ctxt_mgmt_def_pol
from conda.cli.python_api import Commands, run_command
from conda.common.io import env_var
from conda.core.solve import get_pinned_specs
from conda.exceptions import PackagesNotFoundError
from conda.gateways.disk.create import mkdir_p
import conda.instructions as inst
from conda.models.channel import Channel
from conda.models.dist import Dist
from conda.models.records import PackageRecord
from conda.models.match_spec import MatchSpec
from conda.plan import display_actions, add_unlink, add_defaults_to_specs, _update_old_plan as update_old_plan
from conda.exports import execute_plan
from conda.testing.decorators import skip_if_no_mock
from conda.testing.helpers import captured, get_index_r_1, mock, tempdir

from .gateways.disk.test_permissions import tempdir

index, r, = get_index_r_1()
index = index.copy()  # create a shallow copy so this module can mutate state

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


def get_matchspec_from_index(index, match_spec_str):
    ms = MatchSpec(match_spec_str)
    return next(prec for prec in index if ms.match(prec))


def DPkg(s, **kwargs):
    d = Dist(s)
    _kwargs = dict(
        fn=d.to_filename(),
        name=d.name,
        version=d.version,
        build=d.build_string,
        build_number=int(d.build_string.rsplit('_', 1)[-1]),
        channel=d.channel,
        subdir=context.subdir,
        md5="012345789",
    )
    _kwargs.update(kwargs)
    return PackageRecord(**_kwargs)

def solve(specs):
    return [Dist.from_string(fn) for fn in r.solve(specs)]


class add_unlink_TestCase(unittest.TestCase):
    def generate_random_dist(self):
        return "foobar-%s-0" % random.randint(100, 200)

    @contextmanager
    def mock_platform(self, windows=False):
        from conda import plan
        with mock.patch.object(plan, "sys") as sys:
            sys.platform = "win32" if windows else "not win32"
            yield sys

    @skip_if_no_mock
    def test_simply_adds_unlink_on_non_windows(self):
        actions = {}
        dist = Dist.from_string(self.generate_random_dist())
        with self.mock_platform(windows=False):
            add_unlink(actions, dist)
        self.assertIn(inst.UNLINK, actions)
        self.assertEqual(actions[inst.UNLINK], [dist, ])

    @skip_if_no_mock
    def test_adds_to_existing_actions(self):
        actions = {inst.UNLINK: [{"foo": "bar"}]}
        dist = Dist.from_string(self.generate_random_dist())
        with self.mock_platform(windows=False):
            add_unlink(actions, dist)
        self.assertEqual(2, len(actions[inst.UNLINK]))


class TestAddDeaultsToSpec(unittest.TestCase):
    # tests for plan.add_defaults_to_specs(r, linked, specs)

    def check(self, specs, added):
        new_specs = list(specs + added)
        add_defaults_to_specs(r, self.linked, specs)
        specs = [s.split(' (')[0] for s in specs]
        self.assertEqual(specs, new_specs)


def test_display_actions_0():
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'False', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        actions = defaultdict(list)
        actions.update({"FETCH": [
            get_matchspec_from_index(index, "channel-1::sympy==0.7.2=py27_0"),
            get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py27_0"),
        ]})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB
    numpy-1.7.1                |           py27_0         5.7 MB
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""

        actions = defaultdict(list)
        actions.update({
            'PREFIX': '/Users/aaronmeurer/anaconda/envs/test',
            'SYMLINK_CONDA': ['/Users/aaronmeurer/anaconda'],
            'LINK': [
                get_matchspec_from_index(index, "channel-1::python==3.3.2=0"),
                get_matchspec_from_index(index, "channel-1::readline==6.2=0"),
                get_matchspec_from_index(index, "channel-1::sqlite==3.7.13=0"),
                get_matchspec_from_index(index, "channel-1::tk==8.5.13=0"),
                get_matchspec_from_index(index, "channel-1::zlib==1.2.7=0"),
            ]
        })
        with captured() as c:
            display_actions(actions, index)


        assert c.stdout == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following NEW packages will be INSTALLED:

    python:   3.3.2-0 \n\
    readline: 6.2-0   \n\
    sqlite:   3.7.13-0
    tk:       8.5.13-0
    zlib:     1.2.7-0 \n\

"""

        actions['UNLINK'] = actions['LINK']
        actions['LINK'] = []

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following packages will be REMOVED:

    python:   3.3.2-0 \n\
    readline: 6.2-0   \n\
    sqlite:   3.7.13-0
    tk:       8.5.13-0
    zlib:     1.2.7-0 \n\

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
            ],
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    cython: 0.19-py33_0 --> 0.19.1-py33_0

"""

        actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 --> 0.19-py33_0

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==1.5=py33_0'),
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==2.1=py33_1'),
                get_matchspec_from_index(index, 'channel-1::pip==1.3.1=py33_1'),
            ]})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0

The following packages will be REMOVED:

    pip:      1.3.1-py33_1

The following packages will be UPDATED:

    cython:   0.19-py33_0  --> 0.19.1-py33_0

The following packages will be DOWNGRADED:

    dateutil: 2.1-py33_1   --> 1.5-py33_0   \n\

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==2.1=py33_1'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==1.5=py33_0'),
            ],
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""

        actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""


def test_display_actions_show_channel_urls():
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'True', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        actions = defaultdict(list)
        sympy_prec = PackageRecord.from_objects(get_matchspec_from_index(index, 'channel-1::sympy==0.7.2=py27_0'))
        numpy_prec = PackageRecord.from_objects(get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py27_0"))
        numpy_prec.channel = sympy_prec.channel = Channel(None)
        actions.update({
            "FETCH": [
                sympy_prec,
                numpy_prec,
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB  <unknown>
    numpy-1.7.1                |           py27_0         5.7 MB  <unknown>
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""

        actions = defaultdict(list)
        actions.update({
            'PREFIX': '/Users/aaronmeurer/anaconda/envs/test',
            'SYMLINK_CONDA': [
                '/Users/aaronmeurer/anaconda',
            ],
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::python==3.3.2=0'),
                get_matchspec_from_index(index, 'channel-1::readline==6.2=0'),
                get_matchspec_from_index(index, 'channel-1::sqlite==3.7.13=0'),
                get_matchspec_from_index(index, 'channel-1::tk==8.5.13=0'),
                get_matchspec_from_index(index, 'channel-1::zlib==1.2.7=0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following NEW packages will be INSTALLED:

    python:   3.3.2-0  channel-1
    readline: 6.2-0    channel-1
    sqlite:   3.7.13-0 channel-1
    tk:       8.5.13-0 channel-1
    zlib:     1.2.7-0  channel-1

"""

        actions['UNLINK'] = actions['LINK']
        actions['LINK'] = []

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following packages will be REMOVED:

    python:   3.3.2-0  channel-1
    readline: 6.2-0    channel-1
    sqlite:   3.7.13-0 channel-1
    tk:       8.5.13-0 channel-1
    zlib:     1.2.7-0  channel-1

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    cython: 0.19-py33_0 channel-1 --> 0.19.1-py33_0 channel-1

"""

        actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 channel-1 --> 0.19-py33_0 channel-1

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==1.5=py33_0'),
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==2.1=py33_1'),
                get_matchspec_from_index(index, 'channel-1::pip==1.3.1=py33_1'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0 channel-1

The following packages will be REMOVED:

    pip:      1.3.1-py33_1 channel-1

The following packages will be UPDATED:

    cython:   0.19-py33_0  channel-1 --> 0.19.1-py33_0 channel-1

The following packages will be DOWNGRADED:

    dateutil: 2.1-py33_1   channel-1 --> 1.5-py33_0    channel-1

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==2.1=py33_1'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
                get_matchspec_from_index(index, 'channel-1::dateutil==1.5=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 channel-1 --> 0.19.1-py33_0 channel-1
    dateutil: 1.5-py33_0  channel-1 --> 2.1-py33_1    channel-1

"""

        actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 channel-1 --> 0.19-py33_0 channel-1
    dateutil: 2.1-py33_1    channel-1 --> 1.5-py33_0  channel-1

"""

        cython_prec = PackageRecord.from_objects(get_matchspec_from_index(index, 'channel-1::cython==0.19.1=py33_0'))
        dateutil_prec = PackageRecord.from_objects(get_matchspec_from_index(index, 'channel-1::dateutil==1.5=py33_0'))
        cython_prec.channel = dateutil_prec.channel = Channel("my_channel")

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                cython_prec,
                get_matchspec_from_index(index, 'channel-1::dateutil==2.1=py33_1'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
                dateutil_prec,
            ]
        })


        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 channel-1  --> 0.19.1-py33_0 my_channel
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    channel-1 \n\

"""

        actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 channel-1 \n\
    dateutil: 2.1-py33_1    channel-1  --> 1.5-py33_0  my_channel

"""


@pytest.mark.xfail(strict=True, reason="Not reporting link type until refactoring display_actions "
                                       "after txn.verify()")
def test_display_actions_link_type():
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'False', stack_callback=conda_tests_ctxt_mgmt_def_pol):

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 2', 'dateutil-1.5-py33_0 2',
        'numpy-1.7.1-py33_0 2', 'python-3.3.2-0 2', 'readline-6.2-0 2', 'sqlite-3.7.13-0 2', 'tk-8.5.13-0 2', 'zlib-1.2.7-0 2']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython:   0.19.1-py33_0 (softlink)
    dateutil: 1.5-py33_0    (softlink)
    numpy:    1.7.1-py33_0  (softlink)
    python:   3.3.2-0       (softlink)
    readline: 6.2-0         (softlink)
    sqlite:   3.7.13-0      (softlink)
    tk:       8.5.13-0      (softlink)
    zlib:     1.2.7-0       (softlink)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 2',
            'dateutil-2.1-py33_1 2'], 'UNLINK':  ['cython-0.19-py33_0',
                'dateutil-1.5-py33_0']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (softlink)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (softlink)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 2',
            'dateutil-1.5-py33_0 2'], 'UNLINK':  ['cython-0.19.1-py33_0',
                'dateutil-2.1-py33_1']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (softlink)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (softlink)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 1', 'dateutil-1.5-py33_0 1',
        'numpy-1.7.1-py33_0 1', 'python-3.3.2-0 1', 'readline-6.2-0 1', 'sqlite-3.7.13-0 1', 'tk-8.5.13-0 1', 'zlib-1.2.7-0 1']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython:   0.19.1-py33_0
    dateutil: 1.5-py33_0   \n\
    numpy:    1.7.1-py33_0 \n\
    python:   3.3.2-0      \n\
    readline: 6.2-0        \n\
    sqlite:   3.7.13-0     \n\
    tk:       8.5.13-0     \n\
    zlib:     1.2.7-0      \n\

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 1',
            'dateutil-2.1-py33_1 1'], 'UNLINK':  ['cython-0.19-py33_0',
                'dateutil-1.5-py33_0']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 1',
            'dateutil-1.5-py33_0 1'], 'UNLINK':  ['cython-0.19.1-py33_0',
                'dateutil-2.1-py33_1']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 3', 'dateutil-1.5-py33_0 3',
        'numpy-1.7.1-py33_0 3', 'python-3.3.2-0 3', 'readline-6.2-0 3', 'sqlite-3.7.13-0 3', 'tk-8.5.13-0 3', 'zlib-1.2.7-0 3']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython:   0.19.1-py33_0 (copy)
    dateutil: 1.5-py33_0    (copy)
    numpy:    1.7.1-py33_0  (copy)
    python:   3.3.2-0       (copy)
    readline: 6.2-0         (copy)
    sqlite:   3.7.13-0      (copy)
    tk:       8.5.13-0      (copy)
    zlib:     1.2.7-0       (copy)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 3',
            'dateutil-2.1-py33_1 3'], 'UNLINK':  ['cython-0.19-py33_0',
                'dateutil-1.5-py33_0']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (copy)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (copy)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 3',
            'dateutil-1.5-py33_0 3'], 'UNLINK':  ['cython-0.19.1-py33_0',
                'dateutil-2.1-py33_1']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (copy)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (copy)

"""
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'True', stack_callback=conda_tests_ctxt_mgmt_def_pol):

        d = Dist('cython-0.19.1-py33_0.tar.bz2')
        index[d] = PackageRecord.from_objects(index[d], channel='my_channel')

        d = Dist('dateutil-1.5-py33_0.tar.bz2')
        index[d] = PackageRecord.from_objects(index[d], channel='my_channel')

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 3', 'dateutil-1.5-py33_0 3',
        'numpy-1.7.1-py33_0 3', 'python-3.3.2-0 3', 'readline-6.2-0 3', 'sqlite-3.7.13-0 3', 'tk-8.5.13-0 3', 'zlib-1.2.7-0 3']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython:   0.19.1-py33_0 my_channel (copy)
    dateutil: 1.5-py33_0    my_channel (copy)
    numpy:    1.7.1-py33_0  <unknown>  (copy)
    python:   3.3.2-0       <unknown>  (copy)
    readline: 6.2-0         <unknown>  (copy)
    sqlite:   3.7.13-0      <unknown>  (copy)
    tk:       8.5.13-0      <unknown>  (copy)
    zlib:     1.2.7-0       <unknown>  (copy)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 3',
            'dateutil-2.1-py33_1 3'], 'UNLINK':  ['cython-0.19-py33_0',
                'dateutil-1.5-py33_0']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 <unknown>  --> 0.19.1-py33_0 my_channel (copy)
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    <unknown>  (copy)

"""

        actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 3',
            'dateutil-1.5-py33_0 3'], 'UNLINK':  ['cython-0.19.1-py33_0',
                'dateutil-2.1-py33_1']})

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown>  (copy)
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel (copy)

"""


def test_display_actions_features():
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'False', stack_callback=conda_tests_ctxt_mgmt_def_pol):

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be REMOVED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.0=py33_p0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.0-py33_p0 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.0=py33_p0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 [mkl] --> 1.7.1-py33_p0 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        # NB: Packages whose version do not changed are put in UPDATED
        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 --> 1.7.1-py33_p0 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.1-py33_0

"""
    with env_var('CONDA_SHOW_CHANNEL_URLS', 'True', stack_callback=conda_tests_ctxt_mgmt_def_pol):

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0   channel-1
    numpy:  1.7.1-py33_p0 channel-1 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
                get_matchspec_from_index(index, 'channel-1::cython==0.19=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be REMOVED:

    cython: 0.19-py33_0   channel-1
    numpy:  1.7.1-py33_p0 channel-1 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.0=py33_p0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be DOWNGRADED:

    numpy: 1.7.1-py33_p0 channel-1 [mkl] --> 1.7.0-py33_p0 channel-1 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.0=py33_p0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 channel-1 [mkl] --> 1.7.1-py33_p0 channel-1 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        # NB: Packages whose version do not changed are put in UPDATED
        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 channel-1 --> 1.7.1-py33_p0 channel-1 [mkl]

"""

        actions = defaultdict(list)
        actions.update({
            'UNLINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_p0'),
            ],
            'LINK': [
                get_matchspec_from_index(index, 'channel-1::numpy==1.7.1=py33_0'),
            ]
        })

        with captured() as c:
            display_actions(actions, index)

        assert c.stdout == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 channel-1 [mkl] --> 1.7.1-py33_0 channel-1

"""


class TestDeprecatedExecutePlan(unittest.TestCase):

    def test_update_old_plan(self):
        old_plan = ['# plan', 'INSTRUCTION arg']
        new_plan = update_old_plan(old_plan)

        expected = [('INSTRUCTION', 'arg')]
        self.assertEqual(new_plan, expected)

        with self.assertRaises(CondaError):
            update_old_plan(['INVALID'])

    def test_execute_plan(self):
        initial_commands = inst.commands

        def set_commands(cmds):
            inst.commands = cmds
        self.addCleanup(lambda : set_commands(initial_commands))

        def INSTRUCTION_CMD(state, arg):
            INSTRUCTION_CMD.called = True
            INSTRUCTION_CMD.arg = arg

        set_commands({'INSTRUCTION': INSTRUCTION_CMD})

        old_plan = ['# plan', 'INSTRUCTION arg']

        execute_plan(old_plan)

        self.assertTrue(INSTRUCTION_CMD.called)
        self.assertEqual(INSTRUCTION_CMD.arg, 'arg')


def generate_mocked_resolve(pkgs, install=None):
    mock_package = namedtuple("IndexRecord",
                              ["preferred_env", "name", "schannel", "version", "fn"])
    mock_resolve = namedtuple("Resolve", ["get_dists_for_spec", "index", "explicit", "install",
                                          "package_name", "dependency_sort"])

    index = {}
    groups = defaultdict(list)
    for preferred_env, name, schannel, version in pkgs:
        dist = Dist.from_string('%s-%s-0' % (name, version), channel_override=schannel)
        pkg = mock_package(preferred_env=preferred_env, name=name, schannel=schannel,
                           version=version, fn=name)
        groups[name].append(dist)
        index[dist] = pkg

    def get_dists_for_spec(spec, emptyok=False):
        # Here, spec should be a MatchSpec
        res = groups[spec.name]
        if not res and not emptyok:
            raise PackagesNotFoundError((spec,))
        return res

    def get_explicit(spec):
        return True

    def get_install(spec, installed, update_deps=None):
        return install

    def get_package_name(dist):
        return dist.name

    def get_dependency_sort(specs):
        return tuple(spec for spec in specs.values())

    return mock_resolve(get_dists_for_spec=get_dists_for_spec, index=index, explicit=get_explicit,
                        install=get_install, package_name=get_package_name,
                        dependency_sort=get_dependency_sort)


def generate_mocked_record(dist_name):
    mocked_record = namedtuple("Record", ["dist_name"])
    return mocked_record(dist_name=dist_name)


def generate_mocked_context(prefix, root_prefix, envs_dirs):
    mocked_context = namedtuple("Context", ["prefix", "root_prefix", "envs_dirs", "prefix_specified"])
    return mocked_context(prefix=prefix, root_prefix=root_prefix, envs_dirs=envs_dirs, prefix_specified=False)


# class TestDetermineAllEnvs(unittest.TestCase):
#     def setUp(self):
#         self.res = generate_mocked_resolve([
#             ("ranenv", "test-spec", "rando_chnl", "1"),
#             (None, "test-spec", "defaults", "5"),
#             ("test1", "test-spec2", "defaults", "1")
#         ])
#         self.specs = [MatchSpec("test-spec"), MatchSpec("test-spec2")]
#
#     def test_determine_all_envs(self):
#         specs_for_envs = plan.determine_all_envs(self.res, self.specs)
#         expected_output = (plan.SpecForEnv(env=None, spec="test-spec"),
#                            plan.SpecForEnv(env="_test1_", spec="test-spec2"))
#         self.assertEquals(specs_for_envs, expected_output)
#
#     def test_determine_all_envs_with_channel_priority(self):
#         self.res = generate_mocked_resolve([
#             (None, "test-spec", "defaults", "5"),
#             ("ranenv", "test-spec", "rando_chnl", "1"),
#             ("test1", "test-spec2", "defaults", "1")
#         ])
#         prioritized_channel_map = prioritize_channels(tuple(["rando_chnl", "defaults"]))
#         specs_for_envs_w_channel_priority = plan.determine_all_envs(
#             self.res, self.specs, prioritized_channel_map)
#         expected_output = (plan.SpecForEnv(env="_ranenv_", spec="test-spec"),
#                            plan.SpecForEnv(env="_test1_", spec="test-spec2"))
#         self.assertEquals(specs_for_envs_w_channel_priority, expected_output)
#
#     def test_determine_all_envs_no_package(self):
#         specs = [MatchSpec("no-exist")]
#         with pytest.raises(NoPackagesFoundError) as err:
#             plan.determine_all_envs(self.res, specs)
#             assert "no-exist package not found" in str(err)


# class TestEnsurePackageNotDuplicatedInPrivateEnvRoot(unittest.TestCase):
#     def setUp(self):
#         self.linked_in_root = {
#             Dist("test1-1.2.3-bs_7"): generate_mocked_record("test1-1.2.3-bs_7")
#         }
#
#     def test_try_install_duplicate_package_in_root(self):
#         dists_for_envs = [plan.SpecForEnv(env="_env_", spec="test1"),
#                           plan.SpecForEnv(env=None, spec="something")]
#         with pytest.raises(InstallError) as err:
#             plan.ensure_package_not_duplicated_in_private_env_root(
#                 dists_for_envs, self.linked_in_root)
#             assert "Package test1 is already installed" in str(err)
#             assert "Can't install in private environment _env_" in str(err)
#
#     def test_try_install_duplicate_package_in_private_env(self):
#         dists_for_envs = [plan.SpecForEnv(env="_env_", spec="test2"),
#                           plan.SpecForEnv(env=None, spec="test3")]
#         with patch.object(EnvsDirectory, "prefix_if_in_private_env") as mock_prefix:
#             mock_prefix.return_value = "some/prefix"
#             with pytest.raises(InstallError) as err:
#                 plan.ensure_package_not_duplicated_in_private_env_root(
#                     dists_for_envs, self.linked_in_root)
#                 assert "Package test3 is already installed" in str(err)
#                 assert "private_env some/prefix" in str(err)
#
#     def test_try_install_no_duplicate(self):
#         dists_for_envs = [plan.SpecForEnv(env="_env_", spec="test2"),
#                           plan.SpecForEnv(env=None, spec="test3")]
#         plan.ensure_package_not_duplicated_in_private_env_root(dists_for_envs, self.linked_in_root)


# # Includes testing for determine_dists_per_prefix and match_to_original_specs
# class TestGroupDistsForPrefix(unittest.TestCase):
#     def setUp(self):
#         pkgs = [
#             (None, "test-spec", "default", "1"),
#             ("ranenv", "test-spec", "default", "5"),
#             ("test1", "test-spec2", "default", "1")]
#         self.res = generate_mocked_resolve(pkgs)
#         self.specs = [MatchSpec("test-spec"), MatchSpec("test-spec2")]
#
#         self.root_prefix = root_prefix = create_temp_location()
#         mkdir_p(join(root_prefix, 'conda-meta'))
#         touch(join(root_prefix, 'conda-meta', 'history'))
#
#         self.context = generate_mocked_context(root_prefix, root_prefix,
#                                                [join(root_prefix, 'envs'),
#                                                 join(root_prefix, 'envs', '_pre_')])
#
#     def tearDown(self):
#         rm_rf(self.root_prefix)
#
#     def test_determine_dists_per_prefix_1(self):
#         with patch.object(plan, "get_resolve_object") as get_resolve_object:
#             get_resolve_object.return_value = self.res
#             preferred_envs_with_specs = {None: ["test-spec", "test-spec2"]}
#             specs_for_prefix = plan.determine_dists_per_prefix(
#                 self.root_prefix, self.res.index, preferred_envs_with_specs, self.context)
#         expected_output = [plan.SpecsForPrefix(
#             prefix=self.root_prefix, r=self.res, specs={"test-spec", "test-spec2"})]
#         self.assertEquals(specs_for_prefix, expected_output)
#
#     def test_determine_dists_per_prefix_2(self):  # not_requires
#         root_prefix = self.root_prefix
#         with env_var("CONDA_ROOT_PREFIX", root_prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
#             with env_var("CONDA_ENVS_DIRS", join(root_prefix, 'envs'), stack_callback=conda_tests_ctxt_mgmt_def_pol):
#                 with patch.object(plan, "get_resolve_object") as gen_resolve_object_mock:
#                     gen_resolve_object_mock.return_value = self.res
#                     preferred_envs_with_specs = {None: ['test-spec', 'test-spec2'], 'ranenv': ['test']}
#                     specs_for_prefix = plan.determine_dists_per_prefix(
#                         root_prefix, self.res.index, preferred_envs_with_specs, self.context)
#                     expected_output = [
#                         plan.SpecsForPrefix(prefix=join(root_prefix, 'envs', '_ranenv_'),
#                                             r=gen_resolve_object_mock(),
#                                             specs={"test"}),
#                         plan.SpecsForPrefix(prefix=root_prefix, r=self.res,
#                                             specs=IndexedSet(("test-spec", "test-spec2")))
#                     ]
#                 self.assertEquals(expected_output, specs_for_prefix)
#
#     def test_match_to_original_specs(self):
#         str_specs = ["test 1.2.0", "test-spec 1.1*", "test-spec2 <4.3"]
#         test_r = self.res
#         grouped_specs = [
#             plan.SpecsForPrefix(prefix="some/prefix/envs/_ranenv_",
#                                 r=test_r,
#                                 specs=IndexedSet(("test",))),
#             plan.SpecsForPrefix(prefix="some/prefix", r=self.res,
#                                 specs=IndexedSet(("test-spec", "test-spec2")))]
#         matched = plan.match_to_original_specs(str_specs, grouped_specs)
#         expected_output = [
#             plan.SpecsForPrefix(prefix="some/prefix/envs/_ranenv_",
#                                 r=test_r,
#                                 specs=["test 1.2.0"]),
#             plan.SpecsForPrefix(prefix="some/prefix", r=self.res,
#                                 specs=["test-spec 1.1*", "test-spec2 <4.3"])]
#
#         assert len(matched) == len(expected_output)
#         assert matched == expected_output


class TestGetActionsForDist(unittest.TestCase):
    def setUp(self):
        self.pkgs = [
            (None, "test-spec", "defaults", "1"),
            ("ranenv", "test-spec", "defaults", "5"),
            (None, "test-spec2", "defaults", "1"),
            ("ranenv", "test", "defaults", "1.2.0")]
        self.res = generate_mocked_resolve(self.pkgs)

    # TODO: ensure_linked_actions is going away; only used in plan._remove_actions
    # @patch("conda.core.linked_data.is_linked", return_value=True)
    # def test_ensure_linked_actions_all_linked(self, load_meta):
    #     dists = [Dist("test-88"), Dist("test-spec-42"), Dist("test-spec2-8.0.0.0.1-9")]
    #     prefix = "some/prefix"
    #
    #     link_actions = plan.ensure_linked_actions(dists, prefix)
    #
    #     expected_output = defaultdict(list)
    #     expected_output["PREFIX"] = prefix
    #     expected_output["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT',
    #                                    'RM_EXTRACTED', 'EXTRACT', 'UNLINK', 'LINK',
    #                                    'SYMLINK_CONDA')
    #     self.assertEquals(link_actions, expected_output)
    #
    # @patch("conda.core.linked_data.is_linked", return_value=False)
    # def test_ensure_linked_actions_no_linked(self, load_meta):
    #     dists = [Dist("test-88"), Dist("test-spec-42"), Dist("test-spec2-8.0.0.0.1-9")]
    #     prefix = "some/prefix"
    #
    #     link_actions = plan.ensure_linked_actions(dists, prefix)
    #
    #     expected_output = defaultdict(list)
    #     expected_output["PREFIX"] = prefix
    #     expected_output["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT',
    #                                    'RM_EXTRACTED', 'EXTRACT', 'UNLINK', 'LINK',
    #                                    'SYMLINK_CONDA')
    #     expected_output["LINK"] = [Dist("test-88"), Dist("test-spec-42"), Dist("test-spec2-8.0.0.0.1-9")]
    #     self.assertEquals(link_actions, expected_output)

    # def test_get_actions_for_dist(self):
    #     install = [Dist("test-1.2.0-py36_7")]
    #     r = generate_mocked_resolve(self.pkgs, install)
    #     dists_for_prefix = plan.SpecsForPrefix(prefix="some/prefix/envs/_ranenv_", r=r,
    #                                            specs=["test 1.2.0"])
    #     actions = plan.get_actions_for_dists(dists_for_prefix, None, self.res.index, None, False,
    #                                          False, True, True)
    #
    #     expected_output = defaultdict(list)
    #     expected_output["PREFIX"] = "some/prefix/envs/_ranenv_"
    #     expected_output["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT',
    #                                    'RM_EXTRACTED', 'EXTRACT', 'UNLINK', 'LINK',
    #                                    'SYMLINK_CONDA')
    #     expected_output["LINK"] = [Dist("test-1.2.0-py36_7")]
    #     expected_output["SYMLINK_CONDA"] = [context.root_dir]
    #
    #     self.assertEquals(actions, expected_output)
    #
    # def test_get_actions_multiple_dists(self):
    #     install = [Dist("testspec2-4.3.0-1"), Dist("testspecs-1.1.1-4")]
    #     r = generate_mocked_resolve(self.pkgs, install)
    #     dists_for_prefix = plan.SpecsForPrefix(prefix="root/prefix", r=r,
    #                                            specs=["testspec2 <4.3", "testspecs 1.1*"])
    #     actions = plan.get_actions_for_dists(dists_for_prefix, None, self.res.index, None, False,
    #                                          False, True, True)
    #
    #     expected_output = defaultdict(list)
    #     expected_output["PREFIX"] = "root/prefix"
    #     expected_output["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT',
    #                                    'RM_EXTRACTED', 'EXTRACT', 'UNLINK', 'LINK',
    #                                    'SYMLINK_CONDA')
    #     expected_output["LINK"] = [Dist("testspec2-4.3.0-1"), Dist("testspecs-1.1.1-4")]
    #     expected_output["SYMLINK_CONDA"] = [context.root_dir]
    #
    #     assert actions == expected_output
    #
    # @patch("conda.core.linked_data.load_linked_data", return_value=[Dist("testspec1-0.9.1-py27_2")])
    # def test_get_actions_multiple_dists_and_unlink(self, load_linked_data):
    #     install = [Dist("testspec2-4.3.0-2"), Dist("testspec1-1.1.1-py27_0")]
    #     r = generate_mocked_resolve(self.pkgs, install)
    #     dists_for_prefix = plan.SpecsForPrefix(prefix="root/prefix", r=r,
    #                                            specs=["testspec2 <4.3", "testspec1 1.1*"])
    #
    #     test_link_data = {"root/prefix": {Dist("testspec1-0.9.1-py27_2"): True}}
    #     with patch("conda.core.linked_data.linked_data_", test_link_data):
    #         actions = plan.get_actions_for_dists(dists_for_prefix, None, self.res.index, None, False,
    #                                          False, True, True)
    #
    #     expected_output = defaultdict(list)
    #     expected_output["PREFIX"] = "root/prefix"
    #     expected_output["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT',
    #                                    'RM_EXTRACTED', 'EXTRACT', 'UNLINK', 'LINK',
    #                                    'SYMLINK_CONDA')
    #     expected_output["LINK"] = [Dist("testspec2-4.3.0-2"), Dist("testspec1-1.1.1-py27_0")]
    #     expected_output["UNLINK"] = [Dist("testspec1-0.9.1-py27_2")]
    #
    #     expected_output["SYMLINK_CONDA"] = [context.root_dir]
    #     assert expected_output["LINK"] == actions["LINK"]
    #     assert actions == expected_output


def generate_remove_action(prefix, unlink):
    action = defaultdict(list)
    action["op_order"] = ('CHECK_FETCH', 'RM_FETCHED', 'FETCH', 'CHECK_EXTRACT', 'RM_EXTRACTED',
                          'EXTRACT', 'UNLINK', 'LINK', 'SYMLINK_CONDA')
    action["PREFIX"] = prefix
    action["UNLINK"] = unlink
    return action


# class TestAddUnlinkOptionsForUpdate(unittest.TestCase):
#     def setUp(self):
#         pkgs = [
#             (None, "test1", "default", "1.0.1"),
#             ("env", "test1", "default", "2.1.4"),
#             ("env", "test2", "default", "1.1.1"),
#             (None, "test3", "default", "1.2.0"),
#             (None, "test4", "default", "1.2.1")]
#         self.res = generate_mocked_resolve(pkgs)
#
#     # @patch("conda.plan.remove_actions", return_value=generate_remove_action(
#     #     "root/prefix", [Dist("test1-2.1.4-1")]))
#     def test_update_in_private_env_add_remove_action(self):  # remove_actions
#         with tempdir() as root_prefix:
#             mkdir_p(join(root_prefix, 'conda-meta'))
#             touch(join(root_prefix, 'conda-meta', 'history'))
#             with env_var("CONDA_ROOT_PREFIX", root_prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
#                 with env_var("CONDA_ENVS_DIRS", join(root_prefix, 'envs'), stack_callback=conda_tests_ctxt_mgmt_def_pol):
#                     with patch("conda.plan.remove_actions",
#                                return_value=generate_remove_action(root_prefix, [Dist("test1-2.1.4-1")])):
#                         preferred_env_prefix = join(root_prefix, 'envs', '_env_')
#                         required_solves = [plan.SpecsForPrefix(prefix=preferred_env_prefix,
#                                                                specs=["test1", "test2"], r=self.res),
#                                            plan.SpecsForPrefix(prefix=context.root_prefix,
#                                                                specs=["test3"],
#                                                                r=self.res)]
#
#                         action = defaultdict(list)
#                         action["PREFIX"] = preferred_env_prefix
#                         action["LINK"] = [Dist("test1-2.1.4-1"), Dist("test2-1.1.1-8")]
#                         actions = [action]
#
#                         test_link_data = {root_prefix: {Dist("test1-2.1.4-1"): True}}
#                         with patch("conda.core.linked_data.linked_data_", test_link_data):
#                             plan.add_unlink_options_for_update(actions, required_solves,
#                                                                self.res.index)
#
#                         expected_output = [action, generate_remove_action(root_prefix,
#                                                                           [Dist("test1-2.1.4-1")])]
#                         self.assertEquals(actions, expected_output)
#
#     @patch("conda.plan.remove_actions", return_value=generate_remove_action(
#         "root/prefix", [Dist("test1-2.1.4-1")]))
#     def test_update_in_private_env_append_unlink(self, remove_actions):
#         required_solves = [plan.SpecsForPrefix(prefix="root/prefix/envs/_env_",
#                                                specs=["test1", "test2"], r=self.res),
#                            plan.SpecsForPrefix(prefix=context.root_prefix, specs=["whatevs"],
#                                                r=self.res)]
#
#         action = defaultdict(list)
#         action["PREFIX"] = "root/prefix/envs/_env_"
#         action["LINK"] = [Dist("test1-2.1.4-1"), Dist("test2-1.1.1-8")]
#         action_root = defaultdict(list)
#         action_root["PREFIX"] = context.root_prefix
#         action_root["LINK"] = [Dist("whatevs-54-54")]
#         actions = [action, action_root]
#
#         test_link_data = {context.root_prefix: {Dist("test1-2.1.4-1"): True}}
#         with patch("conda.core.linked_data.linked_data_", test_link_data):
#             plan.add_unlink_options_for_update(actions, required_solves, self.res.index)
#
#         aug_action_root = defaultdict(list)
#         aug_action_root["PREFIX"] = context.root_prefix
#         aug_action_root["LINK"] = [Dist("whatevs-54-54")]
#         aug_action_root["UNLINK"] = [Dist("test1-2.1.4-1")]
#         expected_output = [action, aug_action_root]
#         self.assertEquals(actions, expected_output)
#
#     def test_update_in_root_env(self):
#         with tempdir() as root_prefix:
#             mkdir_p(join(root_prefix, 'conda-meta'))
#             touch(join(root_prefix, 'conda-meta', 'history'))
#             with env_var("CONDA_ROOT_PREFIX", root_prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
#                 with env_var("CONDA_ENVS_DIRS", join(root_prefix, 'envs'), stack_callback=conda_tests_ctxt_mgmt_def_pol):
#                     env_path = join(root_prefix, 'envs', '_env_')
#                     ed = EnvsDirectory(join(root_prefix, 'envs'))
#                     ed.add_preferred_env_package('_env_', 'test3', join(env_path, "conda-meta", "test3-1.2.0.json"), "test3")
#                     ed.add_preferred_env_package('_env_', 'test4', join(env_path, "conda-meta", "test4-2.1.0-22.json"), "test4")
#                     required_solves = [plan.SpecsForPrefix(prefix=context.root_prefix,
#                                                            specs=["test3", "test4"],
#                                                            r=self.res)]
#
#                     action = defaultdict(list)
#                     action["PREFIX"] = root_prefix
#                     action["LINK"] = [Dist("test3-1.2.0"), Dist("test4-1.2.1")]
#                     actions = [action]
#                     plan.add_unlink_options_for_update(actions, required_solves, self.res.index)
#                     expected_output = [action, generate_remove_action(env_path, [Dist("test3-1.2.0"), Dist("test4-2.1.0-22")])]
#                     self.assertEquals(actions, expected_output)


def test_pinned_specs():
    # Test pinned specs environment variable
    specs_str_1 = ("numpy 1.11", "python >3")
    specs_1 = tuple(MatchSpec(spec_str, optional=True) for spec_str in specs_str_1)
    with env_var('CONDA_PINNED_PACKAGES', '&'.join(specs_str_1), stack_callback=conda_tests_ctxt_mgmt_def_pol):
        pinned_specs = get_pinned_specs("/none")
        assert pinned_specs == specs_1
        assert pinned_specs != specs_str_1

    # Test pinned specs conda environment file
    specs_str_2 = ("scipy ==0.14.2", "openjdk >=8")
    specs_2 = tuple(MatchSpec(spec_str, optional=True) for spec_str in specs_str_2)

    with tempdir() as td:
        mkdir_p(join(td, 'conda-meta'))
        with open(join(td, 'conda-meta', 'pinned'), 'w') as fh:
            fh.write("\n".join(specs_str_2))
            fh.write("\n")
        pinned_specs = get_pinned_specs(td)
        assert pinned_specs == specs_2
        assert pinned_specs != specs_str_2

    # Test pinned specs conda configuration and pinned specs conda environment file
    with tempdir() as td:
        mkdir_p(join(td, 'conda-meta'))
        pinned_filename = join(td, 'conda-meta', 'pinned')
        with open(pinned_filename, 'w') as fh:
            fh.write("\n".join(specs_str_1))
            fh.write("\n")

        with env_var('CONDA_PREFIX', td, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            run_command(Commands.CONFIG, "--env", "--add", "pinned_packages", "requests=2.13")
            condarc = join(td, '.condarc')
            with env_var('CONDA_PINNED_PACKAGES', '&'.join(specs_str_2), partial(stack_context, True, search_path=(condarc,))):#conda_tests_ctxt_mgmt_def_pol):
                pinned_specs = get_pinned_specs(td)
                expected = specs_2 + (MatchSpec("requests 2.13.*", optional=True),) + specs_1
                assert pinned_specs == expected
                assert pinned_specs != specs_str_1 + ("requests 2.13",) + specs_str_2



if __name__ == '__main__':
    unittest.main()
