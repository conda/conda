import unittest

from conda.cli.common import arg2spec, spec_from_line


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13|0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_pip_style(self):
        self.assertEqual(arg2spec('foo>=1.3'), 'foo >=1.3')
        self.assertEqual(arg2spec('zope.int>=1.3,<3.0'), 'zope.int >=1.3,<3.0')
        self.assertEqual(arg2spec('numpy >=1.9'), 'numpy >=1.9')

    def test_invalid(self):
        self.assertRaises(SystemExit, arg2spec, '!xyz 1.3')


class TestSpecFromLine(unittest.TestCase):

    def test_invalid(self):
        self.assertEqual(spec_from_line('='), None)
        self.assertEqual(spec_from_line('foo 1.0'), None)

    def test_conda_style(self):
        self.assertEqual(spec_from_line('foo'), 'foo')
        self.assertEqual(spec_from_line('foo=1.0'), 'foo 1.0')
        self.assertEqual(spec_from_line('foo=1.0*'), 'foo 1.0*')
        self.assertEqual(spec_from_line('foo=1.0|1.2'), 'foo 1.0|1.2')
        self.assertEqual(spec_from_line('foo=1.0=2'), 'foo 1.0 2')

    def test_pip_style(self):
        self.assertEqual(spec_from_line('foo>=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('FOO-Bar >=1.0'), 'foo-bar >=1.0')
        self.assertEqual(spec_from_line('foo >= 1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo > 1.0'), 'foo >1.0')
        self.assertEqual(spec_from_line('foo != 1.0'), 'foo !=1.0')
        self.assertEqual(spec_from_line('foo <1.0'), 'foo <1.0')
        self.assertEqual(spec_from_line('foo >=1.0 , < 2.0'), 'foo >=1.0,<2.0')


if __name__ == '__main__':
    unittest.main()
