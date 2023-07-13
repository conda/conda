============
Pre-commands
============

Conda commands can be extended with the ``conda_pre_commands`` plugin hook.
By specifying the set of commands you would like to use in the ``run_for`` configuration
option, you can execute code via the ``action`` option before these commands are run.
The functions are provided ``command`` and ``args`` arguments which represent the name
of the command currently running and the command line arguments, respectively.

If you would like to target ``conda env`` commands, prefix the command name with ``env_``.
For example, ``conda env list`` would be passed to ``run_for`` as ``env_list``.

.. autoapiclass:: conda.plugins.types.CondaPreCommand
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_commands
