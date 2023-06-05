# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import random
import unittest
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from functools import partial
from os.path import join
from unittest import mock

import pytest
from pytest_mock import MockerFixture

import conda.instructions as inst
from conda import CondaError
from conda.base.context import (
    conda_tests_ctxt_mgmt_def_pol,
    context,
    reset_context,
    stack_context,
)
from conda.cli.python_api import Commands, run_command
from conda.common.io import env_var
from conda.core.solve import get_pinned_specs
from conda.exceptions import PackagesNotFoundError
from conda.exports import execute_plan
from conda.gateways.disk.create import mkdir_p
from conda.models.channel import Channel
from conda.models.dist import Dist
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from conda.plan import _update_old_plan as update_old_plan
from conda.plan import add_defaults_to_specs, add_unlink, display_actions
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.testing.helpers import captured, get_index_r_1

from .gateways.disk.test_permissions import tempdir

index, r = get_index_r_1()
index = index.copy()  # create a shallow copy so this module can mutate state


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
        build_number=int(d.build_string.rsplit("_", 1)[-1]),
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

    def test_simply_adds_unlink_on_non_windows(self):
        actions = {}
        dist = Dist.from_string(self.generate_random_dist())
        with self.mock_platform(windows=False):
            add_unlink(actions, dist)
        self.assertIn(inst.UNLINK, actions)
        self.assertEqual(
            actions[inst.UNLINK],
            [
                dist,
            ],
        )

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
        specs = [s.split(" (")[0] for s in specs]
        self.assertEqual(specs, new_specs)


def test_display_actions_0():
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        actions = defaultdict(list)
        actions.update(
            {
                "FETCH": [
                    get_matchspec_from_index(index, "channel-1::sympy==0.7.2=py27_0"),
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py27_0"),
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB
    numpy-1.7.1                |           py27_0         5.7 MB
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "PREFIX": "/Users/aaronmeurer/anaconda/envs/test",
                "SYMLINK_CONDA": ["/Users/aaronmeurer/anaconda"],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::python==3.3.2=0"),
                    get_matchspec_from_index(index, "channel-1::readline==6.2=0"),
                    get_matchspec_from_index(index, "channel-1::sqlite==3.7.13=0"),
                    get_matchspec_from_index(index, "channel-1::tk==8.5.13=0"),
                    get_matchspec_from_index(index, "channel-1::zlib==1.2.7=0"),
                ],
            }
        )
        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following NEW packages will be INSTALLED:

    python:   3.3.2-0 \n\
    readline: 6.2-0   \n\
    sqlite:   3.7.13-0
    tk:       8.5.13-0
    zlib:     1.2.7-0 \n\

"""
        )

        actions["UNLINK"] = actions["LINK"]
        actions["LINK"] = []

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following packages will be REMOVED:

    python:   3.3.2-0 \n\
    readline: 6.2-0   \n\
    sqlite:   3.7.13-0
    tk:       8.5.13-0
    zlib:     1.2.7-0 \n\

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    cython: 0.19-py33_0 --> 0.19.1-py33_0

"""
        )

        actions["LINK"], actions["UNLINK"] = actions["UNLINK"], actions["LINK"]

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 --> 0.19-py33_0

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==1.5=py33_0"),
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==2.1=py33_1"),
                    get_matchspec_from_index(index, "channel-1::pip==1.3.1=py33_1"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==2.1=py33_1"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==1.5=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""
        )

        actions["LINK"], actions["UNLINK"] = actions["UNLINK"], actions["LINK"]

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""
        )


def test_display_actions_show_channel_urls():
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        actions = defaultdict(list)
        sympy_prec = PackageRecord.from_objects(
            get_matchspec_from_index(index, "channel-1::sympy==0.7.2=py27_0")
        )
        numpy_prec = PackageRecord.from_objects(
            get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py27_0")
        )
        numpy_prec.channel = sympy_prec.channel = Channel(None)
        actions.update(
            {
                "FETCH": [
                    sympy_prec,
                    numpy_prec,
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB  <unknown>
    numpy-1.7.1                |           py27_0         5.7 MB  <unknown>
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "PREFIX": "/Users/aaronmeurer/anaconda/envs/test",
                "SYMLINK_CONDA": [
                    "/Users/aaronmeurer/anaconda",
                ],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::python==3.3.2=0"),
                    get_matchspec_from_index(index, "channel-1::readline==6.2=0"),
                    get_matchspec_from_index(index, "channel-1::sqlite==3.7.13=0"),
                    get_matchspec_from_index(index, "channel-1::tk==8.5.13=0"),
                    get_matchspec_from_index(index, "channel-1::zlib==1.2.7=0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following NEW packages will be INSTALLED:

    python:   3.3.2-0  channel-1
    readline: 6.2-0    channel-1
    sqlite:   3.7.13-0 channel-1
    tk:       8.5.13-0 channel-1
    zlib:     1.2.7-0  channel-1

"""
        )

        actions["UNLINK"] = actions["LINK"]
        actions["LINK"] = []

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##

  environment location: /Users/aaronmeurer/anaconda/envs/test


The following packages will be REMOVED:

    python:   3.3.2-0  channel-1
    readline: 6.2-0    channel-1
    sqlite:   3.7.13-0 channel-1
    tk:       8.5.13-0 channel-1
    zlib:     1.2.7-0  channel-1

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    cython: 0.19-py33_0 channel-1 --> 0.19.1-py33_0 channel-1

"""
        )

        actions["LINK"], actions["UNLINK"] = actions["UNLINK"], actions["LINK"]

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 channel-1 --> 0.19-py33_0 channel-1

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==1.5=py33_0"),
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==2.1=py33_1"),
                    get_matchspec_from_index(index, "channel-1::pip==1.3.1=py33_1"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==2.1=py33_1"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                    get_matchspec_from_index(index, "channel-1::dateutil==1.5=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 channel-1 --> 0.19.1-py33_0 channel-1
    dateutil: 1.5-py33_0  channel-1 --> 2.1-py33_1    channel-1

"""
        )

        actions["LINK"], actions["UNLINK"] = actions["UNLINK"], actions["LINK"]

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 channel-1 --> 0.19-py33_0 channel-1
    dateutil: 2.1-py33_1    channel-1 --> 1.5-py33_0  channel-1

"""
        )

        cython_prec = PackageRecord.from_objects(
            get_matchspec_from_index(index, "channel-1::cython==0.19.1=py33_0")
        )
        dateutil_prec = PackageRecord.from_objects(
            get_matchspec_from_index(index, "channel-1::dateutil==1.5=py33_0")
        )
        cython_prec.channel = dateutil_prec.channel = Channel("my_channel")

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    cython_prec,
                    get_matchspec_from_index(index, "channel-1::dateutil==2.1=py33_1"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                    dateutil_prec,
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    cython:   0.19-py33_0 channel-1  --> 0.19.1-py33_0 my_channel
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    channel-1 \n\

"""
        )

        actions["LINK"], actions["UNLINK"] = actions["UNLINK"], actions["LINK"]

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 channel-1 \n\
    dateutil: 2.1-py33_1    channel-1  --> 1.5-py33_0  my_channel

"""
        )


@pytest.mark.xfail(
    strict=True,
    reason="Not reporting link type until refactoring display_actions "
    "after txn.verify()",
)
def test_display_actions_link_type():
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        actions = defaultdict(
            list,
            {
                "LINK": [
                    "cython-0.19.1-py33_0 2",
                    "dateutil-1.5-py33_0 2",
                    "numpy-1.7.1-py33_0 2",
                    "python-3.3.2-0 2",
                    "readline-6.2-0 2",
                    "sqlite-3.7.13-0 2",
                    "tk-8.5.13-0 2",
                    "zlib-1.2.7-0 2",
                ]
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19.1-py33_0 2", "dateutil-2.1-py33_1 2"],
                "UNLINK": ["cython-0.19-py33_0", "dateutil-1.5-py33_0"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (softlink)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (softlink)

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19-py33_0 2", "dateutil-1.5-py33_0 2"],
                "UNLINK": ["cython-0.19.1-py33_0", "dateutil-2.1-py33_1"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (softlink)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (softlink)

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": [
                    "cython-0.19.1-py33_0 1",
                    "dateutil-1.5-py33_0 1",
                    "numpy-1.7.1-py33_0 1",
                    "python-3.3.2-0 1",
                    "readline-6.2-0 1",
                    "sqlite-3.7.13-0 1",
                    "tk-8.5.13-0 1",
                    "zlib-1.2.7-0 1",
                ]
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19.1-py33_0 1", "dateutil-2.1-py33_1 1"],
                "UNLINK": ["cython-0.19-py33_0", "dateutil-1.5-py33_0"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19-py33_0 1", "dateutil-1.5-py33_0 1"],
                "UNLINK": ["cython-0.19.1-py33_0", "dateutil-2.1-py33_1"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": [
                    "cython-0.19.1-py33_0 3",
                    "dateutil-1.5-py33_0 3",
                    "numpy-1.7.1-py33_0 3",
                    "python-3.3.2-0 3",
                    "readline-6.2-0 3",
                    "sqlite-3.7.13-0 3",
                    "tk-8.5.13-0 3",
                    "zlib-1.2.7-0 3",
                ]
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19.1-py33_0 3", "dateutil-2.1-py33_1 3"],
                "UNLINK": ["cython-0.19-py33_0", "dateutil-1.5-py33_0"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (copy)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (copy)

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19-py33_0 3", "dateutil-1.5-py33_0 3"],
                "UNLINK": ["cython-0.19.1-py33_0", "dateutil-2.1-py33_1"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (copy)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (copy)

"""
        )
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        d = Dist("cython-0.19.1-py33_0.tar.bz2")
        index[d] = PackageRecord.from_objects(index[d], channel="my_channel")

        d = Dist("dateutil-1.5-py33_0.tar.bz2")
        index[d] = PackageRecord.from_objects(index[d], channel="my_channel")

        actions = defaultdict(
            list,
            {
                "LINK": [
                    "cython-0.19.1-py33_0 3",
                    "dateutil-1.5-py33_0 3",
                    "numpy-1.7.1-py33_0 3",
                    "python-3.3.2-0 3",
                    "readline-6.2-0 3",
                    "sqlite-3.7.13-0 3",
                    "tk-8.5.13-0 3",
                    "zlib-1.2.7-0 3",
                ]
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
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
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19.1-py33_0 3", "dateutil-2.1-py33_1 3"],
                "UNLINK": ["cython-0.19-py33_0", "dateutil-1.5-py33_0"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 <unknown>  --> 0.19.1-py33_0 my_channel (copy)
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    <unknown>  (copy)

"""
        )

        actions = defaultdict(
            list,
            {
                "LINK": ["cython-0.19-py33_0 3", "dateutil-1.5-py33_0 3"],
                "UNLINK": ["cython-0.19.1-py33_0", "dateutil-2.1-py33_1"],
            },
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown>  (copy)
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel (copy)

"""
        )


def test_display_actions_features():
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be REMOVED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.0=py33_p0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.0-py33_p0 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.0=py33_p0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 [mkl] --> 1.7.1-py33_p0 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        # NB: Packages whose version do not changed are put in UPDATED
        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 --> 1.7.1-py33_p0 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.1-py33_0

"""
        )
    with env_var(
        "CONDA_SHOW_CHANNEL_URLS", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0   channel-1
    numpy:  1.7.1-py33_p0 channel-1 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                    get_matchspec_from_index(index, "channel-1::cython==0.19=py33_0"),
                ]
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be REMOVED:

    cython: 0.19-py33_0   channel-1
    numpy:  1.7.1-py33_p0 channel-1 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.0=py33_p0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be DOWNGRADED:

    numpy: 1.7.1-py33_p0 channel-1 [mkl] --> 1.7.0-py33_p0 channel-1 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.0=py33_p0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 channel-1 [mkl] --> 1.7.1-py33_p0 channel-1 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        # NB: Packages whose version do not changed are put in UPDATED
        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 channel-1 --> 1.7.1-py33_p0 channel-1 [mkl]

"""
        )

        actions = defaultdict(list)
        actions.update(
            {
                "UNLINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_p0"),
                ],
                "LINK": [
                    get_matchspec_from_index(index, "channel-1::numpy==1.7.1=py33_0"),
                ],
            }
        )

        with captured() as c:
            display_actions(actions, index)

        assert (
            c.stdout
            == """
## Package Plan ##


The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 channel-1 [mkl] --> 1.7.1-py33_0 channel-1

"""
        )


class TestDeprecatedExecutePlan(unittest.TestCase):
    def test_update_old_plan(self):
        old_plan = ["# plan", "INSTRUCTION arg"]
        new_plan = update_old_plan(old_plan)

        expected = [("INSTRUCTION", "arg")]
        self.assertEqual(new_plan, expected)

        with self.assertRaises(CondaError):
            update_old_plan(["INVALID"])

    def test_execute_plan(self):
        initial_commands = inst.commands

        def set_commands(cmds):
            inst.commands = cmds

        self.addCleanup(lambda: set_commands(initial_commands))

        def INSTRUCTION_CMD(state, arg):
            INSTRUCTION_CMD.called = True
            INSTRUCTION_CMD.arg = arg

        set_commands({"INSTRUCTION": INSTRUCTION_CMD})

        old_plan = ["# plan", "INSTRUCTION arg"]

        execute_plan(old_plan)

        self.assertTrue(INSTRUCTION_CMD.called)
        self.assertEqual(INSTRUCTION_CMD.arg, "arg")


def generate_mocked_resolve(pkgs, install=None):
    mock_package = namedtuple(
        "IndexRecord", ["preferred_env", "name", "schannel", "version", "fn"]
    )
    mock_resolve = namedtuple(
        "Resolve",
        [
            "get_dists_for_spec",
            "index",
            "explicit",
            "install",
            "package_name",
            "dependency_sort",
        ],
    )

    index = {}
    groups = defaultdict(list)
    for preferred_env, name, schannel, version in pkgs:
        dist = Dist.from_string(f"{name}-{version}-0", channel_override=schannel)
        pkg = mock_package(
            preferred_env=preferred_env,
            name=name,
            schannel=schannel,
            version=version,
            fn=name,
        )
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

    return mock_resolve(
        get_dists_for_spec=get_dists_for_spec,
        index=index,
        explicit=get_explicit,
        install=get_install,
        package_name=get_package_name,
        dependency_sort=get_dependency_sort,
    )


def generate_mocked_record(dist_name):
    mocked_record = namedtuple("Record", ["dist_name"])
    return mocked_record(dist_name=dist_name)


def generate_mocked_context(prefix, root_prefix, envs_dirs):
    mocked_context = namedtuple(
        "Context", ["prefix", "root_prefix", "envs_dirs", "prefix_specified"]
    )
    return mocked_context(
        prefix=prefix,
        root_prefix=root_prefix,
        envs_dirs=envs_dirs,
        prefix_specified=False,
    )


class TestGetActionsForDist(unittest.TestCase):
    def setUp(self):
        self.pkgs = [
            (None, "test-spec", "defaults", "1"),
            ("ranenv", "test-spec", "defaults", "5"),
            (None, "test-spec2", "defaults", "1"),
            ("ranenv", "test", "defaults", "1.2.0"),
        ]
        self.res = generate_mocked_resolve(self.pkgs)


def generate_remove_action(prefix, unlink):
    action = defaultdict(list)
    action["op_order"] = (
        "CHECK_FETCH",
        "RM_FETCHED",
        "FETCH",
        "CHECK_EXTRACT",
        "RM_EXTRACTED",
        "EXTRACT",
        "UNLINK",
        "LINK",
        "SYMLINK_CONDA",
    )
    action["PREFIX"] = prefix
    action["UNLINK"] = unlink
    return action


def test_pinned_specs_CONDA_PINNED_PACKAGES():
    # Test pinned specs environment variable
    specs = ("numpy 1.11", "python >3")
    with env_var(
        "CONDA_PINNED_PACKAGES",
        "&".join(specs),
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        pinned_specs = get_pinned_specs("/none")
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_conda_meta_pinned(tmp_env: TmpEnvFixture):
    # Test pinned specs conda environment file
    specs = ("scipy ==0.14.2", "openjdk >=8")
    with tmp_env() as prefix:
        (prefix / "conda-meta" / "pinned").write_text("\n".join(specs) + "\n")

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_condarc(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    # Test pinned specs conda environment file
    specs = ("requests ==2.13",)
    with tmp_env() as prefix:
        # mock active prefix
        mocker.patch(
            "conda.base.context.Context.active_prefix",
            new_callable=mocker.PropertyMock,
            return_value=str(prefix),
        )

        conda_cli("config", "--env", "--add", "pinned_packages", *specs)

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_all(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    # Test pinned specs conda configuration and pinned specs conda environment file
    specs1 = ("numpy 1.11", "python >3")
    specs2 = ("scipy ==0.14.2", "openjdk >=8")
    specs3 = ("requests=2.13",)
    specs = (*specs1, *specs3, *specs2)
    with tmp_env() as prefix, env_var(
        "CONDA_PINNED_PACKAGES",
        "&".join(specs1),
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        (prefix / "conda-meta" / "pinned").write_text("\n".join(specs2) + "\n")

        # mock active prefix
        mocker.patch(
            "conda.base.context.Context.active_prefix",
            new_callable=mocker.PropertyMock,
            return_value=str(prefix),
        )

        conda_cli("config", "--env", "--add", "pinned_packages", *specs3)

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)
