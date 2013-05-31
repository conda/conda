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

    def test_1(self):
        linked = solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        for specs, output in [
            (['python 3*'],  ['python 3*']),
            (['python'],     ['python', 'python 2.7*']),
            (['scipy'],      ['scipy', 'python 2.7*', 'numpy 1.7*']),
            ]:
            plan.add_defaults_to_specs(r, linked, specs)
            self.assertEqual(specs, output)

    def test_2(self):
        linked = solve(['anaconda 1.5.0', 'python 2.6*', 'numpy 1.6*'])
        for specs, output in [
            (['python'],     ['python', 'python 2.6*']),
            (['numpy'],      ['numpy',  'python 2.6*', 'numpy 1.6*']),
            (['pandas'],     ['pandas', 'python 2.6*', 'numpy 1.6*']),
            ]:
            plan.add_defaults_to_specs(r, linked, specs)
            self.assertEqual(specs, output)

    def test_3(self):
        linked = solve(['anaconda 1.5.0', 'python 3.3*'])
        for specs, output in [
            (['python'],     ['python', 'python 3.3*']),
            (['scipy'],      ['scipy', 'python 3.3*', 'numpy 1.7*']),
            ]:
            plan.add_defaults_to_specs(r, linked, specs)
            self.assertEqual(specs, output)

    def test_4(self):
        linked = []
        for specs, output in [
            (['python'],     ['python', 'python 2.7*']),
            (['numpy'],      ['numpy', 'python 2.7*', 'numpy 1.7*']),
            (['scipy'],      ['scipy', 'python 2.7*', 'numpy 1.7*']),
            ]:
            plan.add_defaults_to_specs(r, linked, specs)
            self.assertEqual(specs, output)


if __name__ == '__main__':
    unittest.main()
