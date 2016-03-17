from __future__ import absolute_import
import subprocess

from conda.cli import common
from conda_env.conda_pip import pip_args


def install(prefix, specs, args, env):
    pip_cmd = pip_args(prefix) + ['install', ] + specs
    process = subprocess.Popen(pip_cmd, universal_newlines=True)
    process.communicate()

    if process.returncode != 0:
        common.exception_and_exit(ValueError("pip returned an error."))
