=================
Reporter Backends
=================

Reporter backends are a plugin hook that allow you to change the look and feel
of conda. Each reporter backend contains an implementation of the
:class:`~.conda.plugins.types.ReporterRendererBase` class. This is an abstract base class
that contains all the methods a plugin author must implement in order to change the look
and feel of conda. If only overriding a subset of these is desired, a sub class of
an existing reporter backend can be used.

To configure a reporter backend, you must use the ``reporter_backends`` setting. This setting
allows you to configure different backends for console and json output. Console output is
the normal output you see when using conda and json output is what is render when the
``--json`` option is provided or ``json`` is set to ``true`` in the ``.condarc`` file.

Below is an example showing the configuration for the default reporter backend for ``console``
which is ``classic``:

.. code-block:: yaml

   reporter_backends:
     console:
       backend: classic


.. autoapiclass:: conda.plugins.types.CondaReporterBackend
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_reporter_backends
