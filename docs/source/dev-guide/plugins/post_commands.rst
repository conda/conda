=============
Post-commands
=============

Conda commands can be extended with the ``conda_post_commands`` plugin hook.
By specifying the set of commands you would like to use in the ``run_for`` configuration
option, you can execute code via the ``action`` option after these commands are run.
The functions are provided a ``command`` argument representing the name
of the command currently running. If the command fails for any reason, this plugin hook will not
be run.

If you would like to target ``conda env`` commands, prefix the command name with ``env_``.
For example, ``conda env list`` would be passed to ``run_for`` as ``env_list``.

.. autoapiclass:: conda.plugins.types.CondaPostCommand
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_post_commands
