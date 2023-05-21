import sys


from conda.common.compat import ensure_text_type
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.activate import PosixActivator
from conda.exceptions import conda_exception_handler

from .. import CondaShellPlugins, hookimpl

def handle_env(*args, **kwargs):
    '''
    Export existing activate/reactivate/deactivate logic to a plugin.
    Would work in conjunction with a modified version of conda.sh that forwards
    to the plugin, rather than to an internally-defined activate process.
    A similar process to conda init would inject code into the user's shell profile
    to set the associated shell script as conda's entry point.
    '''
    # cleanup argv
    # this can be updated to use argparse, in line with the os_exec approach
    env_args = sys.argv[2:]  # drop executable/script and sub-command
    env_args = tuple(ensure_text_type(s) for s in env_args)

    context.__init__()
    init_loggers(context)

    activator = PosixActivator(env_args)
    print(activator.execute(), end="")

    return 0

def handle_exceptions(*args, **kwargs):
    '''
    Return the appropriate error code if an exception occurs.
    These are handled through main.py and __main__.py during the current
    activate/reactivate/deactivate process.
    '''

    return sys.exit(conda_exception_handler(handle_env, *args, **kwargs))

@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells that calls the conda processes used for activate, deactivate, and reactivate",
        action=handle_exceptions
    )