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


Example
-------


.. code-block:: python

   def example_command(args):
       print("Example command!")


   @conda.plugins.hookimp
   def conda_cli_register_subcommands(self):
       yield plugins.CondaSubcommand(
           name="example",
           summary="example command",
           action=example_command,
       )
