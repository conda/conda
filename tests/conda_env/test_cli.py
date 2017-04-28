import json
import os
import unittest
import tempfile
from shlex import split

import pytest

from conda_env.exceptions import SpecNotFound
from conda_env.cli.main import create_parser

from conda.base.context import context
from conda.base.constants import ROOT_ENV_NAME
from conda.common.io import captured
from conda.install import rm_rf
from conda.cli.main_create import configure_parser as conda_create_parser
from conda.cli.main_list import configure_parser as list_parser
from conda.cli.main_info import configure_parser as info_parser
from conda.cli.main_install import configure_parser as install_parser
from conda.cli.main import generate_parser

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

test_env_name_1 = "env-1"
test_env_name_2 = "snowflakes"

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
    p = create_parser()
    prefix = escape_for_winpath(prefix)

    if arguments:
        arguments = list(map(escape_for_winpath, arguments))

    if command is Commands.ENV_EXPORT:
        command_line = "{0} -n {1} {2}".format(command, prefix, " ".join(arguments))
    elif command is Commands.ENV_CREATE: # CREATE
        if prefix :
            command_line = "{0} -f {1}  {2}".format(command, prefix, " ".join(arguments))
        else:
            command_line = "{0} ".format(command)
    elif command is Commands.ENV_REMOVE:  # REMOVE
        command_line = "{0} --yes -n {1} {2}".format(command, prefix, " ".join(arguments))
    elif command is Commands.ENV_UPDATE:
        command_line = "{0} -n {1} {2}".format(command, prefix, " ".join(arguments))
    else:
        command_line = " --help "

    args = p.parse_args(split(command_line))
    context._set_argparse_args(args)

    with captured() as c:
        args.func(args, p)

    return c.stdout, c.stderr

parser_config = {
    Commands.CREATE: conda_create_parser,
    Commands.LIST: list_parser,
    Commands.INFO: info_parser,
    Commands.INSTALL: install_parser
}


def run_conda_command(command, prefix, *arguments):
    """
        Run conda command,
    Args:
        command: conda create , list, info
        prefix: The prefix or the name of environment
        *arguments: Extra arguments
    """
    p, sub_parsers = generate_parser()
    assert command in parser_config, "Wrong command for conda {0}".format(command)
    parser_config[command](sub_parsers)

    prefix = escape_for_winpath(prefix)
    if arguments:
        arguments = list(map(escape_for_winpath, arguments))
    if command is Commands.INFO:    # INFO
        command_line = "{0} {1}".format(command, " ".join(arguments))
    elif command is Commands.LIST:  # LIST
        command_line = "{0} -n {1} {2}".format(command, prefix, " ".join(arguments))
    else:  # CREATE
        command_line = "{0} -y -q -n {1} {2}".format(command, prefix, " ".join(arguments))

    args = p.parse_args(split(command_line))
    context._set_argparse_args(args)
    with captured() as c:
        args.func(args, p)

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
        if env_is_created(test_env_name_1):
            run_env_command(Commands.ENV_REMOVE, test_env_name_1)

    def tearDown(self):
        rm_rf("environment.yml")
        if env_is_created(test_env_name_1):
            run_env_command(Commands.ENV_REMOVE, test_env_name_1)

    def test_conda_env_create_no_file(self):
        '''
        Test `conda env create` without an environment.yml file
        Should fail
        '''
        try:
            run_env_command(Commands.ENV_CREATE, None)
        except Exception as e:
            self.assertIsInstance(e, SpecNotFound)


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
            len([env for env in parsed['envs'] if env.endswith(test_env_name_1)]),
            0
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
        # smoke test for gh-254
        create_env(environment_1)
        try:
            run_env_command(Commands.ENV_CREATE, test_env_name_1, "create")
        except Exception as e:
            self.assertIsInstance(e, SpecNotFound, str(e))


def env_is_created(env_name):
    """
        Assert an environment is created
    Args:
        env_name: the environment name
    Returns: True if created
             False otherwise
    """
    from conda import misc
    from os.path import  basename

    for prefix in misc.list_prefixes():
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
        if env_is_created(test_env_name_2):
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))

    def tearDown(self):
        if env_is_created(test_env_name_2):
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))

    def test_create_env(self):
        """
            Test conda create env and conda env remove env
        """
        run_conda_command(Commands.CREATE, test_env_name_2)
        self.assertTrue(env_is_created(test_env_name_2))

    def test_export(self):
        """
            Test conda env export
        """

        run_conda_command(Commands.CREATE, test_env_name_2, "flask")
        self.assertTrue(env_is_created(test_env_name_2))

        snowflake, e,  = run_env_command(Commands.ENV_EXPORT, test_env_name_2)

        with tempfile.NamedTemporaryFile(mode="w", suffix="yml", delete=False) as env_yaml:
            env_yaml.write(snowflake)
            env_yaml.flush()
            env_yaml.close()
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            run_env_command(Commands.ENV_CREATE, env_yaml.name)
            self.assertTrue(env_is_created(test_env_name_2))

    def test_list(self):
        """
            Test conda list -e and conda create from txt
        """

        run_conda_command(Commands.CREATE, test_env_name_2)
        self.assertTrue(env_is_created(test_env_name_2))

        snowflake, e = run_conda_command(Commands.LIST, test_env_name_2, "-e")

        with tempfile.NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
            env_txt.write(snowflake)
            env_txt.flush()
            env_txt.close()
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            run_conda_command(Commands.CREATE, test_env_name_2, "--file " + env_txt.name)
            self.assertTrue(env_is_created(test_env_name_2))

        snowflake2, e = run_conda_command(Commands.LIST, test_env_name_2, "-e")
        self.assertEqual(snowflake, snowflake2)

    def test_export_muti_channel(self):
        """
            Test conda env export
        """

        run_conda_command(Commands.CREATE, test_env_name_2, "python=3.5")
        self.assertTrue(env_is_created(test_env_name_2))

        # install something from other channel not in config file
        run_conda_command(Commands.INSTALL, test_env_name_2, "-c", "numba", "llvmlite")
        snowflake, e, = run_env_command(Commands.ENV_EXPORT, test_env_name_2)
        assert 'numba' in snowflake

        check1, e = run_conda_command(Commands.LIST, test_env_name_2, "--explicit")

        with tempfile.NamedTemporaryFile(mode="w", suffix="yml", delete=False) as env_yaml:
            env_yaml.write(snowflake)
            env_yaml.flush()
            env_yaml.close()
            run_env_command(Commands.ENV_REMOVE, test_env_name_2)
            self.assertFalse(env_is_created(test_env_name_2))
            run_env_command(Commands.ENV_CREATE, env_yaml.name)
            self.assertTrue(env_is_created(test_env_name_2))

        # check explicit that we have same file
        check2, e = run_conda_command(Commands.LIST, test_env_name_2, "--explicit")
        self.assertEqual(check1, check2)

if __name__ == '__main__':
    unittest.main()
