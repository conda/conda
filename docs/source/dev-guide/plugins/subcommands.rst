===========
Subcommands
===========

The conda CLI can be extended with the ``conda_subcommands`` plugin hook.
Registered subcommands will be available under the ``conda <subcommand>``
command.

.. autoapiclass:: conda.plugins.types.CondaSubcommand
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_subcommands
