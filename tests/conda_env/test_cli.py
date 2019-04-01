import json
import os
from conda._vendor.auxlib.compat import Utf8NamedTemporaryFile
import unittest

import pytest

from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context
from conda.cli.conda_argparse import do_call
from conda.cli.main import generate_parser
from conda.common.io import captured
from conda.core.envs_manager import list_all_known_prefixes
from conda.install import rm_rf
from conda.utils import massage_arguments
from conda_env.cli.main import create_parser, do_call as do_call_conda_env
from conda_env.exceptions import EnvironmentFileExtensionNotValid, EnvironmentFileNotFound
from conda_env.yaml import load as yaml_load

from . import support_file

environment_1 = '''
name: env-1
dependencies:
  - python
channels:
  - malev
'''

environment_2 = '''
name: env-1
dependencies:
  - python
  - flask
channels:
  - malev
'''

environment_3_invalid = '''
name: env-1
dependecies:
  - python
  - flask
channels:
  - malev
foo: bar
'''

test_env_name_1 = "env-1"
test_env_name_2 = "snowflakes"
test_env_name_42 = "env-42"


def escape_for_winpath(p):
    if p:
        return p.replace('\\', '\\\\')


class Commands:
    ENV_CREATE = "create"
    ENV_REMOVE = "remove"
    ENV_EXPORT = "export"
    ENV_UPDATE = "update"
    LIST = "list"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"


def run_env_command(command, prefix, *arguments):
    """
        Run conda env commands
    Args:
        command: The command, create, remove, export
        prefix: The prefix, for remove and create
        *arguments: The extra arguments
    """

    arguments = massage_arguments(arguments)
    arguments.insert(0, command)

    if command is Commands.ENV_EXPORT:
        arguments[1:1] = ['-n', prefix]
    elif command is Commands.ENV_CREATE: # CREATE
        if prefix:
            arguments[1:1] = ['-n', prefix]
    elif command is Commands.ENV_REMOVE:  # REMOVE
        arguments[1:1] = ['--yes', '-n', prefix]
    elif command is Commands.ENV_UPDATE:
        arguments[1:1] = ['-n', prefix]
    else:
        command_line = " --help "
    p = create_parser()
    args = p.parse_args(arguments)
    context._set_argparse_args(args)

    with captured() as c:
        do_call_conda_env(args, p)

    return c.stdout, c.stderr


def run_conda_command(command, prefix, *arguments):
    """
        Run conda command,
    Args:
        command: conda create, list, info
        prefix: The prefix or the name of environment
        *arguments: Extra arguments
    """
    p = generate_parser()

    prefix = escape_for_winpath(prefix)
    if arguments:
        arguments = list(map(escape_for_winpath, arguments))
    if command is Commands.INFO:    # INFO
        command_line = "{0} {1}".format(command, " ".join(arguments))
    elif command is Commands.LIST:  # LIST
        command_line = "{0} -n {1} {2}".format(command, prefix, " ".join(arguments))
    else:  # CREATE
        command_line = "{0} -y -q -n {1} {2}".format(command, prefix, " ".join(arguments))

    from conda._vendor.auxlib.compat import shlex_split_unicode
    commands = shlex_split_unicode(command_line)
    args = p.parse_args(commands)
    context._set_argparse_args(args)
    with captured() as c:
        do_call(args, p)

    return c.stdout, c.stderr


def create_env(content, filename='environment.yml'):
    with open(filename, 'w') as fenv:
        fenv.write(content)


def remove_env_file(filename='environment.yml'):
    os.remove(filename)


@pytest.mark.integration
class IntegrationTests(unittest.TestCase):

    def setUp(self):
        rm_rf("environment.yml")
        run_env_command(Commands.ENV_REMOVE, test_env_name_1)
        run_env_command(Commands.ENV_REMOVE, test_env_name_42)

    def tearDown(self):
        rm_rf("environment.yml")
        run_env_command(Commands.ENV_REMOVE, test_env_name_1)
        run_env_command(Commands.ENV_REMOVE, test_env_name_42)

    def test_conda_env_create_no_file(self):
        '''
        Test `conda env create` without an environment.yml file
        Should fail
        '''
        try:
            run_env_command(Commands.ENV_CREATE, None)
        except Exception as e:
            self.assertIsInstance(e, EnvironmentFileNotFound)

    def test_conda_env_create_no_existent_file(self):
        '''
        Test `conda env create --file=not_a_file.txt` with a file that does not
        exist.
        '''
        try:
            run_env_command(Commands.ENV_CREATE, None, '--file', 'not_a_file.txt')
        except Exception as e:
            self.assertIsInstance(e, EnvironmentFileNotFound)

    def test_create_valid_remote_env(self):
        run_env_command(Commands.ENV_CREATE, None, 'goanpeca/env-42')
        self.assertTrue(env_is_created(test_env_name_42))

        o, e = run_conda_command(Commands.INFO, None, "--json")

        parsed = json.loads(o)
        self.assertNotEqual(
            len([env for env in parsed['envs'] if env.endswith(test_env_name_42)]), 0
        )

    def test_create_valid_env(self):
        '''
        Creates an environment.yml file and
        creates and environment with it
        '''

        create_env(environment_1)
        run_env_command(Commands.ENV_CREATE, None)
        self.assertTrue(env_is_created(test_env_name_1))

        o, e = run_conda_command(Commands.INFO, None, "--json")
        parsed = json.loads(o)
        self.assertNotEqual(
            len([env for env in parsed['envs'] if env.endswith(test_env_name_1)]), 0
        )

    def test_update(self):
        create_env(environment_1)
        run_env_command(Commands.ENV_CREATE, None)
        create_env(environment_2)

        run_env_command(Commands.ENV_UPDATE, test_env_name_1)

        o, e = run_conda_command(Commands.LIST, test_env_name_1, "flask", "--json")
        parsed = json.loads(o)
        self.assertNotEqual(len(parsed), 0)

    def test_name(self):
        """
        # smoke test for gh-254
        Test that --name can overide the `name` key inside an environment.yml
        """
        create_env(environment_1)
        env_name = 'smoke-gh-254'

        # It might be the case that you need to run this test more than once!
        try:
            run_env_command(Commands.ENV_REMOVE, env_name)
        except:
            pass

        try:
            run_env_command(Commands.ENV_CREATE, 'environment.yml', "-n",
                            env_name)
        except Exception as e:
            print(e)

        o, e = run_conda_command(Commands.INFO, None, "--json")

        parsed = json.loads(o)
        self.assertNotEqual(
            len([env for env in parsed['envs'] if env.endswith(env_name)]), 0
        )


def env_is_created(env_name):
    """
        Assert an environment is created
    Args:
        env_name: the environment name
    Returns: True if created
             False otherwise
    """
    from os.path import basename

    for prefix in list_all_known_prefixes():
        name = (ROOT_ENV_NAME if prefix == context.root_dir else
                basename(prefix))
        if name == env_name:
            return True

    return False


@pytest.mark.integration
class NewIntegrationTests(unittest.TestCase):
    """
        This is integration test for conda env
        make sure all instruction on online documentation works
        Please refer to link below
        http://conda.pydata.org/docs/using/envs.html#export-the-environment-file
    """

    def setUp(self):
        # It *can* happen that this does not remove the env directory and then
        # the CREATE fails. Keep your eyes out! We could use rm_rf, but do we
        # know which conda install we're talking about? Now? Forever? I'd feel
        # safer adding an `rm -rf` if we had a `Commands.ENV_NAME_TO_PREFIX` to
        # tell us which folder to remove.
        run_env_command(Commands.ENV_REMOVE, test_env_name_2)

    def tearDown(self):
        pass
        run_env_command(Commands.ENV_REMOVE, test_env_name_2)

    def test_env_export(self):
        """
            Test conda env export
        """

        run_conda_command(Commands.CREATE, test_env_name_2, "flask")
        assert env_is_created(test_env_name_2)

        snowflake, e, = run_env_command(Commands.ENV_EXPORT, test_env_name_2)

        with Utf8NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as env_yaml:
            env_yaml.write(snowflake)
            env_yaml.flush()
            env_yaml.close()

            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            run_env_command(Commands.ENV_CREATE, None, "--file", env_yaml.name)
            self.assertTrue(env_is_created(test_env_name_2))

            # regression test for #6220
            snowflake, e, = run_env_command(Commands.ENV_EXPORT, test_env_name_2, '--no-builds')
            assert not e.strip()
            env_description = yaml_load(snowflake)
            assert len(env_description['dependencies'])
            for spec_str in env_description['dependencies']:
                assert spec_str.count('=') == 1

        run_env_command(Commands.ENV_REMOVE, test_env_name_2)
        assert not env_is_created(test_env_name_2)


    def test_list(self):
        """
            Test conda list -e and conda create from txt
        """

        run_conda_command(Commands.CREATE, test_env_name_2)
        self.assertTrue(env_is_created(test_env_name_2))

        snowflake, e = run_conda_command(Commands.LIST, test_env_name_2, "-e")

        with Utf8NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as env_txt:
            env_txt.write(snowflake)
            env_txt.flush()
            env_txt.close()
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            run_conda_command(Commands.CREATE, test_env_name_2, "--file " + env_txt.name)
            self.assertTrue(env_is_created(test_env_name_2))

        snowflake2, e = run_conda_command(Commands.LIST, test_env_name_2, "-e")
        self.assertEqual(snowflake, snowflake2)

    def test_export_multi_channel(self):
        """
            Test conda env export
        """
        from conda.core.prefix_data import PrefixData
        PrefixData._cache_.clear()
        run_conda_command(Commands.CREATE, test_env_name_2, "python=3.5")
        self.assertTrue(env_is_created(test_env_name_2))

        # install something from other channel not in config file
        run_conda_command(Commands.INSTALL, test_env_name_2, "-c", "numba", "llvmlite")
        snowflake, e, = run_env_command(Commands.ENV_EXPORT, test_env_name_2)
        assert 'numba' in snowflake

        check1, e = run_conda_command(Commands.LIST, test_env_name_2, "--explicit")

        with Utf8NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as env_yaml:
            env_yaml.write(snowflake)
            env_yaml.flush()
            env_yaml.close()
            o, e = run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            o, e = run_env_command(Commands.ENV_CREATE, None, "--file", env_yaml.name)
            self.assertTrue(env_is_created(test_env_name_2))

        # check explicit that we have same file
        check2, e = run_conda_command(Commands.LIST, test_env_name_2, "--explicit")
        self.assertEqual(check1, check2)

    def test_non_existent_file(self):
        with self.assertRaises(EnvironmentFileNotFound):
            run_env_command(Commands.ENV_CREATE, None, "--file", 'i_do_not_exist.yml')

    def test_invalid_extensions(self):
        with Utf8NamedTemporaryFile(mode="w", suffix=".ymla", delete=False) as env_yaml:
            with self.assertRaises(EnvironmentFileExtensionNotValid):
                run_env_command(Commands.ENV_CREATE, None, "--file", env_yaml.name)



if __name__ == '__main__':
    unittest.main()
