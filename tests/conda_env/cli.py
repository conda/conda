import json
import os
import unittest
import subprocess

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
    def assertStatusOk(self, status):
        self.assertEqual(status, 0)

    def assertStatusNotOk(self, status):
        self.assertNotEqual(0, status)

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
        self.assertStatusNotOk(s)

    def test_create_valid_env(self):
        '''
        Creates an environment.yml file and
        creates and environment with it
        '''
        create_env(environment_1)

        o, e, s = run('conda env create')
        self.assertStatusOk(s)

        o, e, s = run('conda info --json')
        parsed = json.loads(o)
        self.assertNotEqual(
            len([env for env in parsed['envs'] if env.endswith('env-1')]),
            0
        )

        o, e, s = run('conda env remove -y -n env-1')
        self.assertStatusOk(s)

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
        self.assertStatusOk(s)

if __name__ == '__main__':
    unittest.main()
