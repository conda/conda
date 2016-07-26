from collections import OrderedDict
import os
import sys
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
        self.output += chunk.decode('utf-8')


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
        self.assertEqual(0, len(e.dependencies))

    def test_parses_dependencies_from_raw_file(self):
        e = get_simple_environment()
        expected = OrderedDict([('conda', ['nltk'])])
        self.assertEqual(e.dependencies, expected)

    def test_builds_spec_from_line_raw_dependency(self):
        # TODO Refactor this inside conda to not be a raw string
        e = env.Environment(dependencies=['nltk=3.0.0=np18py27'])
        expected = OrderedDict([('conda', ['nltk 3.0.0 np18py27'])])
        self.assertEqual(e.dependencies, expected)

    def test_args_are_wildcarded(self):
        e = env.Environment(dependencies=['python=2.7'])
        expected = OrderedDict([('conda', ['python 2.7*'])])
        self.assertEqual(e.dependencies, expected)

    def test_other_tips_of_dependencies_are_supported(self):
        e = env.Environment(
            dependencies=['nltk', {'pip': ['foo', 'bar']}]
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

    def test_add_channels(self):
        e = env.Environment()
        e.add_channels(['dup', 'dup', 'unique'])
        self.assertEqual(e.channels, ['dup', 'unique'])

    def test_remove_channels(self):
        e = env.Environment(channels=['channel'])
        e.remove_channels()
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
            dependencies=['nodejs']
        )

        expected = {
            'name': random_name,
            'channels': ['javascript'],
            'dependencies': ['nodejs']
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
            dependencies=['nodejs']
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
            dependencies=['nodejs']
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
            dependencies=['nodejs']
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
        e.dependencies.add('bar')

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
        self.assert_('bar' not in e.dependencies['conda'])
        e.dependencies.add('bar')
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


class LoadEnvFromFileAndSaveTestCase(unittest.TestCase):
    env_path = utils.support_file(os.path.join('saved-env', 'environment.yml'))

    def setUp(self):
        with open(self.env_path, "rb") as fp:
            self.original_file_contents = fp.read()
        self.env = env.load_from_directory(self.env_path)

    def tearDown(self):
        with open(self.env_path, "wb") as fp:
            fp.write(self.original_file_contents)

    def test_expected_default_conditions(self):
        self.assertEqual(1, len(self.env.dependencies['conda']))

    def test(self):
        self.env.dependencies.add('numpy')
        self.env.save()

        e = env.load_from_directory(self.env_path)
        self.assertEqual(2, len(e.dependencies['conda']))
        self.assert_('numpy' in e.dependencies['conda'])


class EnvironmentSaveTestCase(unittest.TestCase):
    env_file = utils.support_file('saved.yml')

    def tearDown(self):
        if os.path.exists(self.env_file):
            os.unlink(self.env_file)

    def test_creates_file_on_save(self):
        self.assertFalse(os.path.exists(self.env_file), msg='sanity check')

        e = env.Environment(filename=self.env_file, name='simple')
        e.save()

        self.assertTrue(os.path.exists(self.env_file))

    def _test_saves_yaml_representation_of_file(self):
        e = env.Environment(filename=self.env_file, name='simple')
        e.save()

        with open(self.env_file, "rb") as fp:
            actual = fp.read()

        self.assert_(len(actual) > 0, msg='sanity check')
        self.assertEqual(e.to_yaml(), actual)
