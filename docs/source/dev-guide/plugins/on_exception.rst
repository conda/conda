=============================
On-Exception (Generic Plugin)
=============================

The conda CLI can be extended with the ``conda_on_exception`` plugin hook.
Registered on-exception actions will be available under the ``{PLUGIN_NAME}_on_exception`` command.

.. autoclass:: conda.plugins.types.CondaOnException
   :members:
   :undoc-members:

.. autofunction:: conda.plugins.hookspec.CondaSpecs.conda_on_exception
