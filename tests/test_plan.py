import json
import unittest
from os.path import dirname, join

import conda.plan as plan
from conda.resolve import Resolve


with open(join(dirname(__file__), 'index.json')) as fi:
    r = Resolve(json.load(fi))

def solve(specs):
    return [fn[:-8] for fn in r.solve(specs)]


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
            (['scipy'],      ['python 2.7*', 'numpy 1.7*']),
            ]:
            self.check(specs, added)

    def test_2(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.6*', 'numpy 1.6*'])
        for specs, added in [
            (['python'],     ['python 2.6*']),
            (['numpy'],      ['python 2.6*', 'numpy 1.6*']),
            (['pandas'],     ['python 2.6*', 'numpy 1.6*']),
            # however, this would then be unsatisfiable
            (['python 3*', 'numpy'], ['numpy 1.6*']),
            ]:
            self.check(specs, added)

    def test_3(self):
        self.linked = solve(['anaconda 1.5.0', 'python 3.3*'])
        for specs, added in [
            (['python'],     ['python 3.3*']),
            (['numpy'],      ['python 3.3*', 'numpy 1.7*']),
            (['scipy'],      ['python 3.3*', 'numpy 1.7*']),
            ]:
            self.check(specs, added)

    def test_4(self):
        self.linked = []
        for specs, added in [
            (['python'],     ['python 2.7*']),
            (['numpy'],      ['python 2.7*', 'numpy 1.7*']),
            (['scipy'],      ['python 2.7*', 'numpy 1.7*']),
            (['anaconda'],   ['python 2.7*', 'numpy 1.7*']),
            (['anaconda 1.5.0 np17py27_0'], []),
            (['anaconda', 'python 3*'],     ['numpy 1.7*']),
            ]:
            self.check(specs, added)


if __name__ == '__main__':
    unittest.main()
