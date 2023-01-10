========================
Pre-Run (Generic Plugin)
========================

The conda CLI can be extended with the ``conda_pre_run`` plugin hook.
Registered pre-run actions will be available under ``{PLUGIN_NAME}_pre_run`` along with
either the ``install`` or ``create`` commands.

.. autoclass:: conda.plugins.types.CondaPreRun
   :members:
   :undoc-members:

.. autofunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_run
