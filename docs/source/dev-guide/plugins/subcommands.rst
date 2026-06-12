===========
Subcommands
===========

The conda CLI can be extended with the ``conda_subcommands`` plugin hook.
Registered subcommands will be available under the ``conda <subcommand>``
command.

Subcommands can provide aliases for alternate command names. Aliases are
registered with the same parser and action as the primary subcommand name, and
must not overlap with built-in commands or other plugin subcommands.

.. autoapiclass:: conda.plugins.types.CondaSubcommand
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_subcommands
