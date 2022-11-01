=================
Conda Subcommands
=================

The Conda CLI can be extended with the ``conda_subcommands`` plugin
hook. Registered subcommands will be available under the ``conda <subcommand>``
command.

Reference
---------

.. automethod:: ~conda.plugins.hookspec.CondaSpecs.conda_subcommands

.. autoclass:: ~conda.models.plugins.CondaSubcommand
   :members:
   :undoc-members:

Example
-------

.. code-block:: python

   def example_command(args):
       print("This is an example command!")


   @conda.plugins.hookimpl
   def conda_subcommands(self):
       yield plugins.CondaSubcommand(
           name="example",
           summary="example command",
           action=example_command,
       )
