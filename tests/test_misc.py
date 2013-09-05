import unittest

from conda.fetch import cache_fn_url


class TestMisc(unittest.TestCase):

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url),
                         '7618c8b65f9329feb96d07caa0751cc6.json')


if __name__ == '__main__':
    unittest.main()
