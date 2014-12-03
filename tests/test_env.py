from collections import OrderedDict
import random
import unittest
import yaml

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import mock
    skip_mocked_tests = False
except ImportError:
    skip_mocked_tests = True

from conda_env import env

from . import utils


def get_simple_environment():
    return env.from_file(utils.support_file('simple.yml'))


class from_file_TestCase(unittest.TestCase):
    def test_returns_Environment(self):
        e = get_simple_environment()
        self.assertIsInstance(e, env.Environment)

    def test_with_pip(self):
        e = env.from_file(utils.support_file('with-pip.yml'))
        self.assert_('pip' in e.dependencies)
        self.assert_('foo' in e.dependencies['pip'])
        self.assert_('baz' in e.dependencies['pip'])


class EnvironmentTestCase(unittest.TestCase):
    def test_has_empty_name_by_default(self):
        e = env.Environment()
        self.assertEqual(e.name, None)

    def test_has_name_if_provided(self):
        random_name = 'random-{}'.format(random.randint(100, 200))
        e = env.Environment(name=random_name)
        self.assertEqual(e.name, random_name)

    def test_dependencies_are_empty_by_default(self):
        e = env.Environment()
        self.assertEqual(e.dependencies, [])

    def test_has_raw_dependencies(self):
        e = get_simple_environment()
        self.assertEqual(e.raw_dependencies, ['nltk'])

    def test_raw_dependencies_default_to_empty_dict(self):
        e = env.Environment()
        self.assertIsInstance(e.raw_dependencies, dict)
        self.assertEqual(e.raw_dependencies, {})

    def test_parses_dependencies_from_raw_dependencies(self):
        e = get_simple_environment()
        expected = OrderedDict([('conda', ['nltk'])])
        self.assertEqual(e.dependencies, expected)

    def test_builds_spec_from_line_raw_dependencies(self):
        # TODO Refactor this inside conda to not be a raw string
        e = env.Environment(raw_dependencies=['nltk=3.0.0=np18py27'])
        expected = OrderedDict([('conda', ['nltk 3.0.0 np18py27'])])
        self.assertEqual(e.dependencies, expected)

    def test_other_tips_of_dependencies_are_supported(self):
        e = env.Environment(
            raw_dependencies=['nltk', {'pip': ['foo', 'bar']}]
        )
        expected = OrderedDict([
            ('conda', ['nltk']),
            ('pip', ['foo', 'bar'])
        ])
        self.assertEqual(e.dependencies, expected)

    def test_channels_default_to_empty_list(self):
        e = env.Environment()
        self.assertIsInstance(e.channels, list)
        self.assertEqual(e.channels, [])

    def test_channels_are_provided_by_kwarg(self):
        random_channels = (random.randint(100, 200), random)
        e = env.Environment(channels=random_channels)
        self.assertEqual(e.channels, random_channels)

    def test_to_dict_returns_dictionary_of_data(self):
        random_name = 'random{}'.format(random.randint(100, 200))
        e = env.Environment(
            name=random_name,
            channels=['javascript'],
            raw_dependencies=['nodejs']
        )

        expected = {
            'name': random_name,
            'channels': ['javascript'],
            'raw_dependencies': ['nodejs']
        }
        self.assertEqual(e.to_dict(), expected)

    def test_to_dict_returns_just_name_if_only_thing_present(self):
        e = env.Environment(name='simple')
        expected = {'name': 'simple'}
        self.assertEqual(e.to_dict(), expected)

    def test_to_yaml_returns_yaml_parseable_string(self):
        random_name = 'random{}'.format(random.randint(100, 200))
        e = env.Environment(
            name=random_name,
            channels=['javascript'],
            raw_dependencies=['nodejs']
        )

        expected = {
            'name': random_name,
            'channels': ['javascript'],
            'dependencies': ['nodejs']
        }

        actual = yaml.load(StringIO(e.to_yaml()))
        self.assertEqual(expected, actual)

    @unittest.skipIf(skip_mocked_tests, 'install mock to run test')
    def test_to_yaml_takes_stream(self):
        random_name = 'random{}'.format(random.randint(100, 200))
        e = env.Environment(
            name=random_name,
            channels=['javascript'],
            raw_dependencies=['nodejs']
        )

        class FakeStream(object):
            def __init__(self):
                self.output = ''

            def write(self, chunk):
                self.output += chunk

        s = FakeStream()
        e.to_yaml(stream=s)

        expected = "\n".join([
            'channels:',
            '- javascript',
            'dependencies:',
            '- nodejs',
            'name: %s' % random_name,
            '',
        ])
        self.assertEqual(expected, s.output)
