=================
Reporter Handlers
=================

Reporter handlers are a plugin hook that allow you to change the look and feel
of conda. Each reporter handler contains an implementation of the
:class:`~.conda.plugins.types.ReporterHandlerBase` class. This is an abstract base class
that contains all the methods a plugin author must implement in order to change the look
and feel of conda. If only overriding a subset of these is desired, a sub class of
an existing reporter handler can be used.

To configure a reporter handler, it must be set as a ``backend`` for the
``reporter`` setting in a configuration file. This setting must contain at least one ``output``
handler.

Below is an example showing the configuration for the default reporter handler ``console`` to
use the ``stdout`` output handler:

.. code-block:: yaml

   reporters:
     - backend: console
       output: stdout


.. autoapiclass:: conda.plugins.types.CondaReporterHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_reporter_handlers
