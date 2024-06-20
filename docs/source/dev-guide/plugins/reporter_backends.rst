=================
Reporter Backends
=================

Reporter backends are a plugin hook that allow you to change the look and feel
of conda. Each reporter backend contains an implementation of the
:class:`~.conda.plugins.types.ReporterRendererBase` class. This is an abstract base class
that contains all the methods a plugin author must implement in order to change the look
and feel of conda. If only overriding a subset of these is desired, a sub class of
an existing reporter backend can be used.

To configure a reporter backend, it must be set as a ``backend`` for the
``reporter`` setting in a configuration file. This setting must configure one ``output``
(e.g. ``stdout``).

Below is an example showing the configuration for the default reporter backend ``console`` to
use the ``stdout`` reporter output:

.. code-block:: yaml

   reporters:
     - backend: console
       output: stdout


.. autoapiclass:: conda.plugins.types.CondaReporterBackend
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_reporter_backends
