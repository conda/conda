======================
Conda Virtual Packages
======================

Conda allows for the registering of virtual packages in the index data via the plugin system. This
mechanism lets users write plugins that provide version identification for proprieties only known
at runtime (e.g., OS information).

Reference
---------

.. automethod:: conda.plugins.hookspec.CondaSpecs.conda_virtual_packages

.. autoclass:: conda.models.plugins.CondaVirtualPackage
   :members:
   :undoc-members:

Example
-------

.. code-block:: python

   def example_command(args):
       print("Example command!")


   @conda.plugins.hookimpl
   def conda_virtual_packages(self):
       yield plugins.CondaVirtualPackage(
           name="my_custom_os",
           version="1.2.3",
       )
