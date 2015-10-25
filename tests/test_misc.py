import unittest

from conda.fetch import cache_fn_url
from conda.misc import url_pat


class TestMisc(unittest.TestCase):

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url), '7618c8b6.json')

    def test_url_pat_1(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2'
                          '#d6918b03927360aa1e57c0188dcb781b')
        self.assertEqual(m.group('url'), 'http://www.cont.io/pkgs/linux-64')
        self.assertEqual(m.group('fn'), 'foo.tar.bz2')
        self.assertEqual(m.group('md5'), 'd6918b03927360aa1e57c0188dcb781b')

    def test_url_pat_2(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2')
        self.assertEqual(m.group('url'), 'http://www.cont.io/pkgs/linux-64')
        self.assertEqual(m.group('fn'), 'foo.tar.bz2')
        self.assertEqual(m.group('md5'), None)

    def test_url_pat_3(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2#1234')
        self.assertEqual(m, None)


if __name__ == '__main__':
    unittest.main()
