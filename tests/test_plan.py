from contextlib import contextmanager
import sys
import json
import random
import unittest
from os.path import dirname, join
from collections import defaultdict

import pytest

from conda.config import default_python, pkgs_dirs
import conda.config
from conda.install import LINK_HARD
import conda.plan as plan
import conda.instructions as inst
from conda.plan import display_actions
from conda.resolve import Resolve

# FIXME This should be a relative import
from tests.helpers import captured
from conda.exceptions import CondaError

from .decorators import skip_if_no_mock
from .helpers import mock

with open(join(dirname(__file__), 'index.json')) as fi:
    index = json.load(fi)
    r = Resolve(index)


def solve(specs):
    return [fn[:-8] for fn in r.solve(specs)]


class TestMisc(unittest.TestCase):

    def test_split_linkarg(self):
        for arg, res in [
            ('w3-1.2-0', ('w3-1.2-0', LINK_HARD)),
            ('w3-1.2-0 1', ('w3-1.2-0', 1)),
            ('w3-1.2-0 1 True', ('w3-1.2-0', 1))]:
            self.assertEqual(inst.split_linkarg(arg), res)


@pytest.mark.parametrize("args", [
    (),
    ("one", ),
    ("one", "two", "three", ),
])
def test_add_unlink_takes_two_arguments(args):
    with pytest.raises(TypeError):
        plan.add_unlink(*args)


class add_unlink_TestCase(unittest.TestCase):
    def generate_random_dist(self):
        return "foobar-%s-0" % random.randint(100, 200)

    @contextmanager
    def mock_platform(self, windows=False):
        with mock.patch.object(plan, "sys") as sys:
            sys.platform = "win32" if windows else "not win32"
            yield sys

    @skip_if_no_mock
    def test_simply_adds_unlink_on_non_windows(self):
        actions = {}
        dist = self.generate_random_dist()
        with self.mock_platform(windows=False):
            plan.add_unlink(actions, dist)
        self.assertIn(inst.UNLINK, actions)
        self.assertEqual(actions[inst.UNLINK], [dist, ])

    @skip_if_no_mock
    def test_adds_to_existing_actions(self):
        actions = {inst.UNLINK: [{"foo": "bar"}]}
        dist = self.generate_random_dist()
        with self.mock_platform(windows=False):
            plan.add_unlink(actions, dist)
        self.assertEqual(2, len(actions[inst.UNLINK]))


class TestAddDeaultsToSpec(unittest.TestCase):
    # tests for plan.add_defaults_to_specs(r, linked, specs)

    def check(self, specs, added):
        new_specs = list(specs + added)
        plan.add_defaults_to_specs(r, self.linked, specs)
        specs = [s.split(' (')[0] for s in specs]
        self.assertEqual(specs, new_specs)

    def test_1(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        for specs, added in [
            (['python 3*'], []),
            (['python'], ['python 2.7*']),
            (['scipy'], ['python 2.7*']),
            ]:
            self.check(specs, added)

    def test_2(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.6*', 'numpy 1.6*'])
        for specs, added in [
            (['python'], ['python 2.6*']),
            (['numpy'], ['python 2.6*']),
            (['pandas'], ['python 2.6*']),
            # however, this would then be unsatisfiable
            (['python 3*', 'numpy'], []),
            ]:
            self.check(specs, added)

    def test_3(self):
        self.linked = solve(['anaconda 1.5.0', 'python 3.3*'])
        for specs, added in [
            (['python'], ['python 3.3*']),
            (['numpy'], ['python 3.3*']),
            (['scipy'], ['python 3.3*']),
            ]:
            self.check(specs, added)

    def test_4(self):
        self.linked = []
        ps = ['python 2.7*'] if default_python == '2.7' else []
        for specs, added in [
            (['python'], ps),
            (['numpy'], ps),
            (['scipy'], ps),
            (['anaconda'], ps),
            (['anaconda 1.5.0 np17py27_0'], []),
            (['sympy 0.7.2 py27_0'], []),
            (['scipy 0.12.0 np16py27_0'], []),
            (['anaconda', 'python 3*'], []),
            ]:
            self.check(specs, added)

def test_display_actions():
    import conda.plan
    conda.plan.config_show_channel_urls = False
    actions = defaultdict(list, {"FETCH": ['sympy-0.7.2-py27_0',
        "numpy-1.7.1-py27_0"]})
    # The older test index doesn't have the size metadata
    index['sympy-0.7.2-py27_0.tar.bz2']['size'] = 4374752
    index["numpy-1.7.1-py27_0.tar.bz2"]['size'] = 5994338

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB
    numpy-1.7.1                |           py27_0         5.7 MB
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""

    actions = defaultdict(list, {'PREFIX':
    '/Users/aaronmeurer/anaconda/envs/test', 'SYMLINK_CONDA':
    ['/Users/aaronmeurer/anaconda'], 'LINK': ['python-3.3.2-0', 'readline-6.2-0 1', 'sqlite-3.7.13-0 1', 'tk-8.5.13-0 1', 'zlib-1.2.7-0 1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
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
The following packages will be REMOVED:

    python:   3.3.2-0 \n\
    readline: 6.2-0   \n\
    sqlite:   3.7.13-0
    tk:       8.5.13-0
    zlib:     1.2.7-0 \n\

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0'], 'UNLINK':
    ['cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython: 0.19-py33_0 --> 0.19.1-py33_0

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython: 0.19.1-py33_0 --> 0.19-py33_0

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-1.5-py33_0', 'numpy-1.7.1-py33_0'], 'UNLINK':
        ['cython-0.19-py33_0', 'dateutil-2.1-py33_1', 'pip-1.3.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0

The following packages will be REMOVED:

    pip:      1.3.1-py33_1

The following packages will be UPDATED:

    cython:   0.19-py33_0  --> 0.19.1-py33_0

The following packages will be DOWNGRADED due to dependency conflicts:

    dateutil: 2.1-py33_1   --> 1.5-py33_0   \n\

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-2.1-py33_1'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']


    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""



def test_display_actions_show_channel_urls():
    import conda.plan
    conda.plan.config_show_channel_urls = True
    actions = defaultdict(list, {"FETCH": ['sympy-0.7.2-py27_0',
        "numpy-1.7.1-py27_0"]})
    # The older test index doesn't have the size metadata
    index['sympy-0.7.2-py27_0.tar.bz2']['size'] = 4374752
    index["numpy-1.7.1-py27_0.tar.bz2"]['size'] = 5994338

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    sympy-0.7.2                |           py27_0         4.2 MB  <unknown>
    numpy-1.7.1                |           py27_0         5.7 MB  <unknown>
    ------------------------------------------------------------
                                           Total:         9.9 MB

"""


    actions = defaultdict(list, {'PREFIX':
    '/Users/aaronmeurer/anaconda/envs/test', 'SYMLINK_CONDA':
    ['/Users/aaronmeurer/anaconda'], 'LINK': ['python-3.3.2-0', 'readline-6.2-0 1', 'sqlite-3.7.13-0 1', 'tk-8.5.13-0 1', 'zlib-1.2.7-0 1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    python:   3.3.2-0  <unknown>
    readline: 6.2-0    <unknown>
    sqlite:   3.7.13-0 <unknown>
    tk:       8.5.13-0 <unknown>
    zlib:     1.2.7-0  <unknown>

"""

    actions['UNLINK'] = actions['LINK']
    actions['LINK'] = []

    with captured() as c:
        display_actions(actions, index)


    assert c.stdout == """
The following packages will be REMOVED:

    python:   3.3.2-0  <unknown>
    readline: 6.2-0    <unknown>
    sqlite:   3.7.13-0 <unknown>
    tk:       8.5.13-0 <unknown>
    zlib:     1.2.7-0  <unknown>

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0'], 'UNLINK':
    ['cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython: 0.19-py33_0 <unknown> --> 0.19.1-py33_0 <unknown>

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']


    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython: 0.19.1-py33_0 <unknown> --> 0.19-py33_0 <unknown>

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-1.5-py33_0', 'numpy-1.7.1-py33_0'], 'UNLINK':
        ['cython-0.19-py33_0', 'dateutil-2.1-py33_1', 'pip-1.3.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0 <unknown>

The following packages will be REMOVED:

    pip:      1.3.1-py33_1 <unknown>

The following packages will be UPDATED:

    cython:   0.19-py33_0  <unknown> --> 0.19.1-py33_0 <unknown>

The following packages will be DOWNGRADED due to dependency conflicts:

    dateutil: 2.1-py33_1   <unknown> --> 1.5-py33_0    <unknown>

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-2.1-py33_1'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 <unknown> --> 0.19.1-py33_0 <unknown>
    dateutil: 1.5-py33_0  <unknown> --> 2.1-py33_1    <unknown>

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 <unknown> --> 0.19-py33_0 <unknown>
    dateutil: 2.1-py33_1    <unknown> --> 1.5-py33_0  <unknown>

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']

    index['cython-0.19.1-py33_0.tar.bz2']['channel'] = 'my_channel'
    index['dateutil-1.5-py33_0.tar.bz2']['channel'] = 'my_channel'

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 <unknown>  --> 0.19.1-py33_0 my_channel
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    <unknown> \n\

"""

    actions['LINK'], actions['UNLINK'] = actions['UNLINK'], actions['LINK']


    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown> \n\
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel

"""


def test_display_actions_link_type():
    import conda.plan
    conda.plan.config_show_channel_urls = False

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 2', 'dateutil-1.5-py33_0 2',
    'numpy-1.7.1-py33_0 2', 'python-3.3.2-0 2', 'readline-6.2-0 2', 'sqlite-3.7.13-0 2', 'tk-8.5.13-0 2', 'zlib-1.2.7-0 2']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython:   0.19.1-py33_0 (soft-link)
    dateutil: 1.5-py33_0    (soft-link)
    numpy:    1.7.1-py33_0  (soft-link)
    python:   3.3.2-0       (soft-link)
    readline: 6.2-0         (soft-link)
    sqlite:   3.7.13-0      (soft-link)
    tk:       8.5.13-0      (soft-link)
    zlib:     1.2.7-0       (soft-link)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 2',
        'dateutil-2.1-py33_1 2'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (soft-link)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (soft-link)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 2',
        'dateutil-1.5-py33_0 2'], 'UNLINK':  ['cython-0.19.1-py33_0',
            'dateutil-2.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (soft-link)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (soft-link)

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
The following packages will be DOWNGRADED due to dependency conflicts:

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
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (copy)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (copy)

"""
    import conda.plan
    conda.plan.config_show_channel_urls = True

    index['cython-0.19.1-py33_0.tar.bz2']['channel'] = 'my_channel'
    index['dateutil-1.5-py33_0.tar.bz2']['channel'] = 'my_channel'

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
The following packages will be DOWNGRADED due to dependency conflicts:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown>  (copy)
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel (copy)

"""

def test_display_actions_features():
    import conda.plan
    conda.plan.config_show_channel_urls = False

    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0', 'cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""

    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0', 'cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be REMOVED:

    cython: 0.19-py33_0  \n\
    numpy:  1.7.1-py33_p0 [mkl]

"""

    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0'], 'LINK': ['numpy-1.7.0-py33_p0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.0-py33_p0 [mkl]

"""

    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0'], 'UNLINK': ['numpy-1.7.0-py33_p0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 [mkl] --> 1.7.1-py33_p0 [mkl]

"""

    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0'], 'UNLINK': ['numpy-1.7.1-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    # NB: Packages whose version do not changed are put in UPDATED
    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 --> 1.7.1-py33_p0 [mkl]

"""

    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0'], 'LINK': ['numpy-1.7.1-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 [mkl] --> 1.7.1-py33_0

"""
    import conda.plan
    conda.plan.config_show_channel_urls = True

    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0', 'cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    cython: 0.19-py33_0   <unknown>
    numpy:  1.7.1-py33_p0 <unknown> [mkl]

"""


    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0', 'cython-0.19-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be REMOVED:

    cython: 0.19-py33_0   <unknown>
    numpy:  1.7.1-py33_p0 <unknown> [mkl]

"""

    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0'], 'LINK': ['numpy-1.7.0-py33_p0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    numpy: 1.7.1-py33_p0 <unknown> [mkl] --> 1.7.0-py33_p0 <unknown> [mkl]

"""

    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0'], 'UNLINK': ['numpy-1.7.0-py33_p0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.0-py33_p0 <unknown> [mkl] --> 1.7.1-py33_p0 <unknown> [mkl]

"""


    actions = defaultdict(list, {'LINK': ['numpy-1.7.1-py33_p0'], 'UNLINK': ['numpy-1.7.1-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    # NB: Packages whose version do not changed are put in UPDATED
    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.1-py33_0 <unknown> --> 1.7.1-py33_p0 <unknown> [mkl]

"""

    actions = defaultdict(list, {'UNLINK': ['numpy-1.7.1-py33_p0'], 'LINK': ['numpy-1.7.1-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    numpy: 1.7.1-py33_p0 <unknown> [mkl] --> 1.7.1-py33_0 <unknown>

"""

def test_display_actions_no_index():
    # Test removing a package that is not in the index. This issue
    # should only come up for removing.
    actions = defaultdict(list, {'UNLINK': ['notinstalled-1.0-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be REMOVED:

    notinstalled: 1.0-py33_0 <unknown>

"""

    actions = defaultdict(list, {"LINK": ['numpy-1.7.1-py33_0'], "UNLINK":
        ['numpy-2.0.0-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    numpy: 2.0.0-py33_1 <unknown> --> 1.7.1-py33_0 <unknown>

"""

    # tk-8.5.13-1 is not in the index. Test that it guesses the build number
    # correctly.
    actions = defaultdict(list, {"LINK": ['tk-8.5.13-0'], "UNLINK":
        ['tk-8.5.13-1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED due to dependency conflicts:

    tk: 8.5.13-1 <unknown> --> 8.5.13-0 <unknown>

"""

class TestDeprecatedExecutePlan(unittest.TestCase):

    def test_update_old_plan(self):
        old_plan = ['# plan', 'INSTRUCTION arg']
        new_plan = plan.update_old_plan(old_plan)

        expected = [('INSTRUCTION', 'arg')]
        self.assertEqual(new_plan, expected)

        with self.assertRaises(CondaError):
            plan.update_old_plan(['INVALID'])

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

        plan.execute_plan(old_plan)


        self.assertTrue(INSTRUCTION_CMD.called)
        self.assertEqual(INSTRUCTION_CMD.arg, 'arg')



class PlanFromActionsTests(unittest.TestCase):
    py_ver = ''.join(str(x) for x in sys.version_info[:2])

    def test_plan_link_menuinst(self):

        menuinst = 'menuinst'
        ipython = 'ipython'
        actions = {
            'PREFIX': 'aprefix',
            'LINK': [ipython, menuinst],
        }

        conda_plan = plan.plan_from_actions(actions)

        expected_plan = [
            ('PREFIX', 'aprefix'),
            ('PRINT', 'Linking packages ...'),
            ('PROGRESS', '2'),
            ('LINK', ipython),
            ('LINK', menuinst),
        ]

        if sys.platform == 'win32':
            # menuinst should be linked first
            expected_plan = [
                ('PREFIX', 'aprefix'),
                ('LINK', menuinst),
                ('PRINT', 'Linking packages ...'),
                ('PROGRESS', '1'),
                ('LINK', ipython),
            ]

            # last_two = expected_plan[-2:]
            # expected_plan[-2:] = last_two[::-1]

        self.assertEqual(expected_plan, conda_plan)

if __name__ == '__main__':
    unittest.main()
