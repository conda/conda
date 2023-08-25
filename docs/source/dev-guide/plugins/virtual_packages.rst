================
Virtual Packages
================

Conda allows for the registering of virtual packages in the index data via
the plugin system. This mechanism lets users write plugins that provide
version identification for properties only known at runtime (e.g., OS
information).

.. autoapiclass:: conda.plugins.types.CondaVirtualPackage
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_virtual_packages
