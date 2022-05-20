=================
Conda Subcommands
=================

The Conda CLI can be extended with the ``conda_cli_register_subcommands`` plugin
hook. Registered subcommands will be available under the ``conda <subcommand>``
command.


Reference
---------


.. py:module:: conda.plugins
   :noindex:

.. autofunction:: conda_cli_register_subcommands

.. autoclass:: CondaSubcommand
   :members:
   :undoc-members:
