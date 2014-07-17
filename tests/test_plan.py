import json
import unittest
from os.path import dirname, join
from collections import defaultdict

from conda.config import default_python, pkgs_dirs
import conda.config
from conda.install import LINK_HARD
import conda.plan as plan
from conda.plan import display_actions
from conda.resolve import Resolve

from tests.helpers import captured

with open(join(dirname(__file__), 'index.json')) as fi:
    index = json.load(fi)
    r = Resolve(index)

def solve(specs):
    return [fn[:-8] for fn in r.solve(specs)]


class TestMisc(unittest.TestCase):

    def test_split_linkarg(self):
        for arg, res in [
            ('w3-1.2-0', ('w3-1.2-0', pkgs_dirs[0], LINK_HARD)),
            ('w3-1.2-0 /opt/pkgs 1', ('w3-1.2-0', '/opt/pkgs', 1)),
            (' w3-1.2-0  /opt/pkgs  1  ', ('w3-1.2-0', '/opt/pkgs', 1)),
            (r'w3-1.2-0 C:\A B\pkgs 2', ('w3-1.2-0', r'C:\A B\pkgs', 2))]:
            self.assertEqual(plan.split_linkarg(arg), res)


class TestAddDeaultsToSpec(unittest.TestCase):
    # tests for plan.add_defaults_to_specs(r, linked, specs)

    def check(self, specs, added):
        new_specs = list(specs + added)
        plan.add_defaults_to_specs(r, self.linked, specs)
        self.assertEqual(specs, new_specs)

    def test_1(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        for specs, added in [
            (['python 3*'],  []),
            (['python'],     ['python 2.7*']),
            (['scipy'],      ['python 2.7*']),
            ]:
            self.check(specs, added)

    def test_2(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.6*', 'numpy 1.6*'])
        for specs, added in [
            (['python'],     ['python 2.6*']),
            (['numpy'],      ['python 2.6*']),
            (['pandas'],     ['python 2.6*']),
            # however, this would then be unsatisfiable
            (['python 3*', 'numpy'], []),
            ]:
            self.check(specs, added)

    def test_3(self):
        self.linked = solve(['anaconda 1.5.0', 'python 3.3*'])
        for specs, added in [
            (['python'],     ['python 3.3*']),
            (['numpy'],      ['python 3.3*']),
            (['scipy'],      ['python 3.3*']),
            ]:
            self.check(specs, added)

    def test_4(self):
        self.linked = []
        ps = ['python 2.7*'] if default_python == '2.7' else []
        for specs, added in [
            (['python'],     ps),
            (['numpy'],      ps),
            (['scipy'],      ps),
            (['anaconda'],   ps),
            (['anaconda 1.5.0 np17py27_0'], []),
            (['sympy 0.7.2 py27_0'], []),
            (['scipy 0.12.0 np16py27_0'], []),
            (['anaconda', 'python 3*'], []),
            ]:
            self.check(specs, added)

def test_display_actions():
    conda.config.show_channel_urls = False
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
    ['/Users/aaronmeurer/anaconda'], 'LINK': ['python-3.3.2-0', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 1', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 1']})

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
The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 --> 0.19-py33_0

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-1.5-py33_0', 'numpy-1.7.1-py33_0'], 'UNLINK':
        ['cython-0.19-py33_0', 'dateutil-2.1-py33_1', 'pip-1.3.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0 \n\

The following packages will be REMOVED:

    pip:      1.3.1-py33_1

The following packages will be UPDATED:

    cython:   0.19-py33_0  --> 0.19.1-py33_0

The following packages will be DOWNGRADED:

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
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""



def test_display_actions_show_channel_urls():
    conda.config.show_channel_urls = True
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
    ['/Users/aaronmeurer/anaconda'], 'LINK': ['python-3.3.2-0', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 1', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 1']})

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
The following packages will be DOWNGRADED:

    cython: 0.19.1-py33_0 <unknown> --> 0.19-py33_0 <unknown>

"""


    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0',
        'dateutil-1.5-py33_0', 'numpy-1.7.1-py33_0'], 'UNLINK':
        ['cython-0.19-py33_0', 'dateutil-2.1-py33_1', 'pip-1.3.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following NEW packages will be INSTALLED:

    numpy:    1.7.1-py33_0  <unknown>

The following packages will be REMOVED:

    pip:      1.3.1-py33_1 <unknown>

The following packages will be UPDATED:

    cython:   0.19-py33_0  <unknown> --> 0.19.1-py33_0 <unknown>

The following packages will be DOWNGRADED:

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
The following packages will be DOWNGRADED:

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
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown> \n\
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel

"""


def test_display_actions_link_type():
    conda.config.show_channel_urls = False

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 2', 'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 2',
    'numpy-1.7.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 2', 'python-3.3.2-0 /Users/aaronmeurer/anaconda/pkgs 2', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 2', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 2', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 2', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 2']})

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

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 2',
        'dateutil-2.1-py33_1 /Users/aaronmeurer/anaconda/pkgs 2'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (soft-link)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (soft-link)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 /Users/aaronmeurer/anaconda/pkgs 2',
        'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 2'], 'UNLINK':  ['cython-0.19.1-py33_0',
            'dateutil-2.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (soft-link)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (soft-link)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 1', 'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 1',
    'numpy-1.7.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 1', 'python-3.3.2-0 /Users/aaronmeurer/anaconda/pkgs 1', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 1', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 1', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 1']})

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

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 1',
        'dateutil-2.1-py33_1 /Users/aaronmeurer/anaconda/pkgs 1'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0
    dateutil: 1.5-py33_0  --> 2.1-py33_1   \n\

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 /Users/aaronmeurer/anaconda/pkgs 1',
        'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 1'], 'UNLINK':  ['cython-0.19.1-py33_0',
            'dateutil-2.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0
    dateutil: 2.1-py33_1    --> 1.5-py33_0 \n\

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3', 'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
    'numpy-1.7.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3', 'python-3.3.2-0 /Users/aaronmeurer/anaconda/pkgs 3', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 3', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 3', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 3', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 3']})

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

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
        'dateutil-2.1-py33_1 /Users/aaronmeurer/anaconda/pkgs 3'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 --> 0.19.1-py33_0 (copy)
    dateutil: 1.5-py33_0  --> 2.1-py33_1    (copy)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
        'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 3'], 'UNLINK':  ['cython-0.19.1-py33_0',
            'dateutil-2.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 --> 0.19-py33_0 (copy)
    dateutil: 2.1-py33_1    --> 1.5-py33_0  (copy)

"""

    conda.config.show_channel_urls = True

    index['cython-0.19.1-py33_0.tar.bz2']['channel'] = 'my_channel'
    index['dateutil-1.5-py33_0.tar.bz2']['channel'] = 'my_channel'

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3', 'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
    'numpy-1.7.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3', 'python-3.3.2-0 /Users/aaronmeurer/anaconda/pkgs 3', 'readline-6.2-0 /Users/aaronmeurer/anaconda/pkgs 3', 'sqlite-3.7.13-0 /Users/aaronmeurer/anaconda/pkgs 3', 'tk-8.5.13-0 /Users/aaronmeurer/anaconda/pkgs 3', 'zlib-1.2.7-0 /Users/aaronmeurer/anaconda/pkgs 3']})

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

    actions = defaultdict(list, {'LINK': ['cython-0.19.1-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
        'dateutil-2.1-py33_1 /Users/aaronmeurer/anaconda/pkgs 3'], 'UNLINK':  ['cython-0.19-py33_0',
            'dateutil-1.5-py33_0']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be UPDATED:

    cython:   0.19-py33_0 <unknown>  --> 0.19.1-py33_0 my_channel (copy)
    dateutil: 1.5-py33_0  my_channel --> 2.1-py33_1    <unknown>  (copy)

"""

    actions = defaultdict(list, {'LINK': ['cython-0.19-py33_0 /Users/aaronmeurer/anaconda/pkgs 3',
        'dateutil-1.5-py33_0 /Users/aaronmeurer/anaconda/pkgs 3'], 'UNLINK':  ['cython-0.19.1-py33_0',
            'dateutil-2.1-py33_1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED:

    cython:   0.19.1-py33_0 my_channel --> 0.19-py33_0 <unknown>  (copy)
    dateutil: 2.1-py33_1    <unknown>  --> 1.5-py33_0  my_channel (copy)

"""

def test_display_actions_features():
    conda.config.show_channel_urls = False

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
The following packages will be DOWNGRADED:

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

    conda.config.show_channel_urls = True

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
The following packages will be DOWNGRADED:

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
The following packages will be DOWNGRADED:

    numpy: 2.0.0-py33_1 <unknown> --> 1.7.1-py33_0 <unknown>

"""

    # tk-8.5.13-1 is not in the index. Test that it guesses the build number
    # correctly.
    actions = defaultdict(list, {"LINK": ['tk-8.5.13-0'], "UNLINK":
        ['tk-8.5.13-1']})

    with captured() as c:
        display_actions(actions, index)

    assert c.stdout == """
The following packages will be DOWNGRADED:

    tk: 8.5.13-1 <unknown> --> 8.5.13-0 <unknown>

"""
