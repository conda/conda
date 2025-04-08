======================
Environment Specifiers
======================

Conda can create environments from several file formats. The available readers
can be extended with additional plugins via the ``conda_environment_specifiers``
hook.

.. autoapiclass:: conda.plugins.types.CondaEnvironmentSpeficier
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_environment_specifiers
