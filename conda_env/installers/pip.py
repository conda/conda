from __future__ import absolute_import
import subprocess
from conda_env.pip_util import pip_args
from conda.exceptions import CondaValueError


def install(prefix, specs, args, env, prune=False):
    pip_cmd = pip_args(prefix) + ['install', ] + specs
    process = subprocess.Popen(pip_cmd, universal_newlines=True)
    process.communicate()

    if process.returncode != 0:
        raise CondaValueError("pip returned an error.")
