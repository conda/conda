=================
Pre-transactions
=================

:ref:`Solver transactions <solver_api_transactions>` can be extended with the
``conda_pre_transaction_actions`` plugin hook. This plugin hook accepts a subclass of
``Action`` which will be instantiated and prepended to conda's transaction
action list. When defining the class you must define the following methods:

* ``execute``: this is the primary place to put code you wish to run during the action.
* ``verify``: this is run before the action is executed. This is a good place to check for
  conditions that would cause the action to fail.
* ``cleanup``: this is run after the action is executed. This is a good place to clean up any
  resources that were created during the action.
* ``reverse``: in the case of a failure, this allows you to define any reversal procedures.

.. autoapiclass:: conda.plugins.types.CondaPreTransactionAction
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_transaction_actions
