=========================
Post-Run (Generic Plugin)
=========================

The conda CLI can be extended with the ``conda_post_run`` plugin hook.
Registered post-run actions will be available under the ``{PLUGIN_NAME}_post_run`` along with
either the ``install`` or ``create`` commands.

.. autoclass:: conda.plugins.types.CondaPostRun
   :members:
   :undoc-members:

.. autofunction:: conda.plugins.hookspec.CondaSpecs.conda_post_run
