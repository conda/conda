=================
Post-transactions
=================

:ref:`Solver transactions <solver_api_transactions>` can be extended with the
``conda_post_transactions`` plugin hook. This plugin hook accepts a function which will be called
after any action is executed, with the action object as the only argument. Arbitrary code can be
executed via this mechanism, but remember that even simple solves can generate thousands of actions
- so running computationally expensive code via this plugin mechanism can be slow.

.. autoapiclass:: conda.plugins.types.CondaPostTransaction
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_post_transactions
