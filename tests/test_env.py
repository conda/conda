from collections import OrderedDict
import os
import random
import textwrap
import unittest
import yaml

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from conda_env import env
from conda_env import exceptions

from . import utils


class FakeStream(object):
    def __init__(self):
        self.output = ''

    def write(self, chunk):
        self.output += chunk


def get_simple_environment():
    return env.from_file(utils.support_file('simple.yml'))


class from_file_TestCase(unittest.TestCase):
    def test_returns_Environment(self):
        e = get_simple_environment()
        self.assertIsInstance(e, env.Environment)

    def test_retains_full_filename(self):
        e = get_simple_environment()
        self.assertEqual(utils.support_file('simple.yml'), e.filename)

    def test_with_pip(self):
        e = env.from_file(utils.support_file('with-pip.yml'))
        self.assert_('pip' in e.dependencies)
        self.assert_('foo' in e.dependencies['pip'])
        self.assert_('baz' in e.dependencies['pip'])


class EnvironmentTestCase(unittest.TestCase):
    def test_has_empty_filename_by_default(self):
        e = env.Environment()
        self.assertEqual(e.filename, None)

    def test_has_filename_if_provided(self):
        r = random.randint(100, 200)
        random_filename = '/path/to/random/environment-{}.yml'.format(r)
        e = env.Environment(filename=random_filename)
        self.assertEqual(e.filename, random_filename)

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

    def test_to_yaml_returns_proper_yaml(self):
        random_name = 'random{}'.format(random.randint(100, 200))
        e = env.Environment(
            name=random_name,
            channels=['javascript'],
            raw_dependencies=['nodejs']
        )

        expected = '\n'.join([
            "name: %s" % random_name,
            "channels:",
            "- javascript",
            "dependencies:",
            "- nodejs",
            ""
        ])

        actual = e.to_yaml()
        self.assertEqual(expected, actual)

    def test_to_yaml_takes_stream(self):
        random_name = 'random{}'.format(random.randint(100, 200))
        e = env.Environment(
            name=random_name,
            channels=['javascript'],
            raw_dependencies=['nodejs']
        )

        s = FakeStream()
        e.to_yaml(stream=s)

        expected = "\n".join([
            'name: %s' % random_name,
            'channels:',
            '- javascript',
            'dependencies:',
            '- nodejs',
            '',
        ])
        self.assertEqual(expected, s.output)

    def test_can_add_dependencies_to_environment(self):
        e = get_simple_environment()
        e.add_dependency('bar')

        s = FakeStream()
        e.to_yaml(stream=s)

        expected = "\n".join([
            'name: nlp',
            'dependencies:',
            '- nltk',
            '- bar',
            ''
        ])
        self.assertEqual(expected, s.output)

    def test_dependencies_update_after_adding(self):
        e = get_simple_environment()
        self.assert_(not 'bar' in e.dependencies['conda'])
        e.add_dependency('bar')
        self.assert_('bar' in e.dependencies['conda'])


class DirectoryTestCase(unittest.TestCase):
    directory = utils.support_file('example')

    def setUp(self):
        self.original_working_dir = os.getcwd()
        self.env = env.load_from_directory(self.directory)

    def tearDown(self):
        os.chdir(self.original_working_dir)

    def test_returns_env_object(self):
        self.assertIsInstance(self.env, env.Environment)

    def test_has_expected_name(self):
        self.assertEqual('test', self.env.name)

    def test_has_dependencies(self):
        self.assertEqual(1, len(self.env.dependencies['conda']))
        self.assert_('numpy' in self.env.dependencies['conda'])


class load_from_directory_example_TestCase(DirectoryTestCase):
    directory = utils.support_file('example')


class load_from_directory_example_yaml_TestCase(DirectoryTestCase):
    directory = utils.support_file('example-yaml')


class load_from_directory_recursive_TestCase(DirectoryTestCase):
    directory = utils.support_file('foo/bar')


class load_from_directory_recursive_two_TestCase(DirectoryTestCase):
    directory = utils.support_file('foo/bar/baz')


class load_from_directory_trailing_slash_TestCase(DirectoryTestCase):
    directory = utils.support_file('foo/bar/baz/')


class load_from_directory_TestCase(unittest.TestCase):
    def test_raises_when_unable_to_find(self):
        with self.assertRaises(exceptions.EnvironmentFileNotFound):
            env.load_from_directory('/path/to/unknown/env-spec')

    def test_raised_exception_has_environment_yml_as_file(self):
        with self.assertRaises(exceptions.EnvironmentFileNotFound) as e:
            env.load_from_directory('/path/to/unknown/env-spec')
        self.assertEqual(e.exception.filename, 'environment.yml')
