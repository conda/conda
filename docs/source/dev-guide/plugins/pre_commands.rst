============
Pre-commands
============

Conda commands can be extended with the ``conda_pre_commands`` plugin hook.
By specifying the set of commands you would like to use in the ``run_for`` configuration
option, you can execute code via the ``action`` option before these commands are run. ``action``
should be a valid callable object.

The ``action`` callable is provided the following arguments:

- ``command``: name of the command currently being invoked
- ``parsed_args``: an ``argparse.Namespace`` object; this will only be populated when the command
   being run is a conda core command (e.g. ``install`` or ``create``)
- ``raw_args``: a list of argument and option strings (e.g. ``['-p', '/tmp/path']``); this will
  only be populated for plugin subcommands (i.e. subcommands that are not part of conda's
  core).

If you would like to target ``conda env`` commands, prefix the command name with ``env_``.
For example, ``conda env list`` would be passed to ``run_for`` as ``env_list``.

.. autoapiclass:: conda.plugins.types.CondaPreCommand
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_commands
