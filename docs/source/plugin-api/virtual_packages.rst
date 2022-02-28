======================
Conda Virtual Packages
======================

Conda allow registering virtual packages in the index data via the plugin
system. This allows users to write plugins that provide version identification
for proprieties only known at runtime for example, like OS information, etc.


Reference
---------


.. py:module:: conda.plugins
   :noindex:

.. autofunction:: conda_cli_register_virtual_packages

.. autoclass:: CondaVirtualPackage
   :members:
   :undoc-members:


Example
-------


.. code-block:: python

   def example_command(args):
       print("Example command!")


   @conda.plugins.hookimp
   def conda_cli_register_subcommands(self):
       yield plugins.CondaVirtualPackage(
           name="my_custom_os",
           version="1.2.3",
       )
