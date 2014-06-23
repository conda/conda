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
