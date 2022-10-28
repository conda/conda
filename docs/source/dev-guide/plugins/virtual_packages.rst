======================
Conda Virtual Packages
======================

Conda allows for the registering of virtual packages in the index data via the plugin system. This
mechanism lets users write plugins that provide version identification for proprieties only known
at runtime (e.g., OS information).


Reference
---------


.. py:module:: conda.plugins
   :noindex:

.. autofunction:: conda_virtual_packages

.. autoclass:: CondaVirtualPackage
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
