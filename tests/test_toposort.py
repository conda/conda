import unittest
from conda.toposort import toposort, pop_key


class TopoSortTests(unittest.TestCase):

    def test_pop_key(self):
        key = pop_key({'a':{'b', 'c'}, 'b':{'c'}})
        self.assertEqual(key, 'b')

        key = pop_key({'a':{'b'}, 'b':{'c', 'a'}})
        self.assertEqual(key, 'a')

        key = pop_key({'a':{'b'}, 'b':{'a'}})
        self.assertEqual(key, 'a')

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

    def test_python_is_prioritized(self):
        """
        This test checks a special invariant related to 'python' specifically.
        Python is part of a cycle (pip <--> python), which can cause it to be
        installed *after* packages that need python (possibly in
        post-install.sh).

        A special case in toposort() breaks the cycle, to ensure that python
        isn't installed too late.  Here, we verify that it works.
        """
        # This is the actual dependency graph for python (as of the time of this writing, anyway)
        data = {'python' : ['pip', 'openssl', 'readline', 'sqlite', 'tk', 'xz', 'zlib'],
                'pip': ['python', 'setuptools', 'wheel'],
                'setuptools' : ['python'],
                'wheel' : ['python'],
                'openssl' : [],
                'readline' : [],
                'sqlite' : [],
                'tk' : [],
                'xz' : [],
                'zlib' : []}

        # Here are some extra pure-python libs, just for good measure.
        data.update({'psutil' : ['python'],
                     'greenlet' : ['python'],
                     'futures' : ['python'],
                     'six' : ['python']})

        results = toposort(data)

        # Python always comes before things that need it!
        self.assertLess(results.index('python'), results.index('setuptools'))
        self.assertLess(results.index('python'), results.index('wheel'))
        self.assertLess(results.index('python'), results.index('pip'))
        self.assertLess(results.index('python'), results.index('psutil'))
        self.assertLess(results.index('python'), results.index('greenlet'))
        self.assertLess(results.index('python'), results.index('futures'))
        self.assertLess(results.index('python'), results.index('six'))

if __name__ == '__main__':
    unittest.main()
