from __future__ import absolute_import
import subprocess

from conda.cli import main_list


def install(prefix, specs, args, env):
    pip_cmd = main_list.pip_args(prefix) + ['install', ] + specs
    process = subprocess.Popen(pip_cmd, universal_newlines=True)
    process.communicate()
