============
Health-checks
============

Conda doctor can be extended with the ``health_checks`` plugin hook.
Write new health checks using the ``health_checks`` plugin hook, install the plugins you wrote and they will run every time ``conda doctor`` command is run.
The ``action`` option is where you specify the code you want to be executed with ``conda doctor``.

.. autoapiclass:: conda.plugins.types.CondaHealthCheck
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_health_check
