import unittest

from conda.cli.common import arg2spec, spec_from_line


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13|0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_invalid_char(self):
        self.assertRaises(SystemExit, arg2spec, 'abc%def')
        self.assertRaises(SystemExit, arg2spec, '!xyz 1.3')

    def test_too_long(self):
        self.assertRaises(SystemExit, arg2spec, 'foo=1.3=2=4')

    def test_spec_from_line(self):
        self.assertEqual(spec_from_line('='), None)

        self.assertEqual(spec_from_line('foo'), 'foo')
        self.assertEqual(spec_from_line('foo=1.0'), 'foo 1.0')
        self.assertEqual(spec_from_line('foo=1.0=2'), 'foo 1.0 2')

        self.assertEqual(spec_from_line('foo>=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >= 1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >=1.0 , < 2.0'), 'foo >=1.0,<2.0')


if __name__ == '__main__':
    unittest.main()
