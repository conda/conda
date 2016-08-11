import json
import os
import unittest
import tempfile
import subprocess
from conda_env.exceptions import SpecNotFound
environment_1 = '''
name: env-1
dependencies:
  - ojota
channels:
  - malev
'''

environment_2 = '''
name: env-1
dependencies:
  - ojota
  - flask
channels:
  - malev
'''


def run(command):
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    status = process.returncode
    return (stdout, stderr, status)


def create_env(content, filename='environment.yml'):
    with open(filename, 'w') as fenv:
        fenv.write(content)


def remove_env_file(filename='environment.yml'):
    os.remove(filename)


class IntegrationTest(unittest.TestCase):
    def tearDown(self):
        run('conda env remove -n env-1 -y')
        run('conda env remove -n env-2 -y')
        run('rm environment.yml')

    def test_conda_env_create_no_file(self):
        '''
        Test `conda env create` without an environment.yml file
        Should fail
        '''
        o, e, s = run('conda env create')
        self.assertRaises(SpecNotFound)

    def test_create_valid_env(self):
        '''
        Creates an environment.yml file and
        creates and environment with it
        '''
        create_env(environment_1)

        o, e, s = run('conda env create')
        self.assertTrue(env_is_created("env-1"))

        o, e, s = run('conda info --json')
        parsed = json.loads(o)
        self.assertNotEqual(
            len([env for env in parsed['envs'] if env.endswith('env-1')]),
            0
        )

        o, e, s = run('conda env remove -y -n env-1')
        self.assertFalse(env_is_created("env-1"))

    def test_update(self):
        create_env(environment_1)
        o, e, s = run('conda env create')
        create_env(environment_2)
        o, e, s = run('conda env update -n env-1')
        o, e, s = run('conda list flask -n env-1 --json')
        parsed = json.loads(o)
        self.assertNotEqual(len(parsed), 0)

    def test_name(self):
        # smoke test for gh-254
        create_env(environment_1)
        o, e, s = run('conda env create -n new-env create')

        self.assertRaises(SpecNotFound)


def env_is_created(env_name):
    """
        Assert an environment is created
    Args:
        env_name: the environment name
    Returns: True if created
             False otherwise
    """
    stdout, stderr, status = run("conda env list")
    stdout_lines = stdout.split('\n')
    for line in stdout_lines:
        line = line.strip()
        if line is None or line.startswith("#"):
            continue
        if env_name in line:
            return True
    return False


class NewIntegrationTest(unittest.TestCase):
    """
        This is integration test for conda env
        make sure all instruction on online documentation works
        Please refer to link below
        http://conda.pydata.org/docs/using/envs.html#export-the-environment-file
    """

    def test_conda_env_help(self):
        """
            Test functionality of conda env --help
        """
        o, _, _ = run("conda env --help")
        message = [ "create", "export", "list", "remove", "upload", "update"]
        for m in message:
            self.assertIn(m, o, o)

    def test_create_env(self):
        """
            Test conda create env and conda env remove env
        """
        if env_is_created("snowflakes"):
            run("conda env remove --yes --name snowflakes")
            self.assertFalse(env_is_created("snowflakes"))

        run("conda create --yes --name snowflakes")
        self.assertTrue(env_is_created("snowflakes"))


        run("conda env remove --yes --name snowflakes")
        self.assertFalse(env_is_created("snowflakes"))

    def test_export(self):
        """
            Test conda env
        """
        if not env_is_created("snowflakes"):
            run("conda create --yes --name snowflakes python")
            self.assertTrue(env_is_created("snowflakes"))

        snowflake, e, s = run("conda env export -n snowflakes")

        with tempfile.NamedTemporaryFile(mode="w", suffix="yml") as env_yaml:
            env_yaml.write(snowflake)
            env_yaml.flush()
            run("conda env remove --yes --name snowflakes")
            self.assertFalse(env_is_created("snowflakes"))
            o, e, s = run("conda env create -f " + env_yaml.name)
            self.assertTrue(env_is_created("snowflakes"))

        o, e, s = run("conda env remove --yes --name snowflakes")
        self.assertFalse(env_is_created("snowflakes"))

    def test_list(self):
        """
            Test conda env
        """
        if not env_is_created("snowflakes"):
            run("conda create --yes --name snowflakes")
            self.assertTrue(env_is_created("snowflakes"))

        snowflake, e, s = run("conda list -n snowflakes -e")

        with tempfile.NamedTemporaryFile(mode="w", suffix="txt") as env_txt:
            env_txt.write(snowflake)
            env_txt.flush()
            run("conda env remove --yes --name snowflakes")
            self.assertFalse(env_is_created("snowflakes"))
            o, e, s = run("conda create -n snowflakes --file " + env_txt.name)
            self.assertTrue(env_is_created("snowflakes"))

        o, e, s = run("conda env remove --yes --name snowflakes")
        self.assertFalse(env_is_created("snowflakes"))

if __name__ == '__main__':
    unittest.main()
