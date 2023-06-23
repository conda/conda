=============
Post-commands
=============

Conda commands can be extended with the ``conda_post_commands`` plugin hook.
By specifying the set of commands you would like to use in the ``run_for`` configuration
option, you can execute code via the ``action`` option after these commands are run. ``action``
should be a valid callable object.

The ``action`` callable is provided the following arguments:

- ``command``: name of the command currently being invoked
- ``parsed_args``: an ``argparse.Namespace`` object; this will only be populated when the command
   being run is a conda core command (e.g. ``install`` or ``create``)
- ``raw_args``: a list of argument and option strings (e.g. ``['-p', '/tmp/path']``); this will
  only be populated for plugin subcommands (i.e. subcommands that are not part of conda's
  core).

If the command fails for any reason, this plugin hook will not be run and the program will
exit normally through conda's exception handler logic.

If you would like to target ``conda env`` commands, prefix the command name with ``env_``.
For example, ``conda env list`` would be passed to ``run_for`` as ``env_list``.

.. autoclass:: conda.plugins.types.CondaPostCommand
   :members:
   :undoc-members:

.. autofunction:: conda.plugins.hookspec.CondaSpecs.conda_post_commands
