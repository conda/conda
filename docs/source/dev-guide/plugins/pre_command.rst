========================
Pre-command
========================

Conda command start-up can be extended with the ``conda_pre_commands`` plugin hook.
By specifying the set of commands you would like to use in the ``run_for`` configuration
option, you can execute code via the ``action`` option before these commands are run.
The functions are provided ``command`` and ``args`` arguments which represent the name
of the command currently running and the command line arguments, respectively.


.. autoclass:: conda.plugins.types.CondaPreCommand
   :members:
   :undoc-members:

.. autofunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_commands
