import unittest
from conda.toposort import toposort

class TopoSortTests(unittest.TestCase):

    def test_simple(self):
        data = {'a':'bc', 'b':'c'}
        results = toposort(data, safe=True)
        self.assertEqual(results, ['c', 'b', 'a'])
        results = toposort(data, safe=False)
        self.assertEqual(results, ['c', 'b', 'a'])

    def test_cycle(self):
        data = {'a':'b', 'b':'a'}

        with self.assertRaises(ValueError):
            toposort(data, False)

        results = toposort(data)
        # Results do not have an guaranteed order
        self.assertEqual(set(results), {'b', 'a'})

    def test_cycle_best_effort(self):
        data = {'a':'bc', 'b':'c', '1':'2', '2':'1'}

        results = toposort(data)
        self.assertEqual(results[:3], ['c', 'b', 'a'])

        # Cycles come last
        # Results do not have an guaranteed order
        self.assertEqual(set(results[3:]), {'1', '2'})


if __name__ == '__main__':
    unittest.main()
