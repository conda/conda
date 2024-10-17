=================
Reporter Backends
=================

Reporter backends is a plugin hook that allows you to customize the display of certain
elements at the command line. Below is a list of all the elements that can currently
be customized:

- Progress bar (displayed during package downloads)
- Spinner (displayed while conda is waiting for a long running task to finish)
- Confirmation input (yes/no dialogs)
- ``conda info`` layout

This can be configured using the ``console`` setting either as a command line option
or by defining it in the ``.condarc`` file.

For more information on configuring and using reporter backends in conda itself see:

- :ref:`Settings: console <console>`

Example plugin
==============

The following example defines a simple plugin which uses the :func:`~pprint.pformat` function for rendering
parts of conda's output:

.. hint::

   This is just a partial example. To see a fully functioning example of a reporter backend,
   checkout the :mod:`~conda.plugins.reporter_backends.console` module.

.. code-block:: python

    from pprint import pformat

    from conda import plugins
    from conda.plugins.types import (
        CondaReporterBackend,
        ReporterRendererBase,
        ProgressBarBase,
    )


    class PprintReporterRenderer(ReporterRendererBase):
        """
        Implementation of the ReporterRendererBase abstract base class
        """

        def detail_view(self, data):
            return pformat(data)

        def envs_list(self, data):
            formatted_data = pformat(data)
            return f"Environments: {formatted_data}"

        def progress_bar(self, description, io_context_manager) -> ProgressBarBase:
            """Returns our custom progress bar implementation"""
            return PprintProgressBar(description, io_context_manager)


    class PprintProgressBar(ProgressBarBase):
        """
        Blank implementation of ProgressBarBase which does nothing.
        """

        def update_to(self, fraction) -> None:
            pass

        def refresh(self) -> None:
            pass

        def close(self) -> None:
            pass


    @plugins.hookimpl
    def conda_reporter_backends():
        yield CondaReporterBackend(
            name="pprint",
            description="Reporter backend based on the pprint module",
            renderer=PprintReporterRenderer,
        )

Below is a summary of everything we've defined:

Defining ``ReporterRendererBase``
---------------------------------

The first class we define, ``PprintReporterRenderer``, is a subclass of
:class:`~conda.plugins.types.ReporterRendererBase`. The base class is an abstract base class which requires us to
define our own implementations of its abstract methods. These abstract methods are used by conda when rendering output
and are where all the customization we want to do occurs.

Defining ``ProgressBarBase``
----------------------------

The second class we define is ``PprintProgressBar``. For this example, it is just an empty implementation of the
:class:`~conda.plugins.types.ProgressBarBase`.  Defining this effectively hides the progress bar
when this reporter backend is configured. We do this in this tutorial because a full implementation would
take too long to explain. Please check out :class:`~conda.plugins.reporter_backends.console.TQDMProgressBar`
for a more realistic example using the `tqdm <https://tqdm.github.io/>`_ library.

Registering the plugin hook
---------------------------

Finally, we define the ``conda_reporter_backends`` function with the ``plugins.hookimpl`` decorator to register
our plugin which returns the ``PprintReporterRenderer`` class wrapped in a
:class:`~conda.plugins.types.CondaReporterBackend` object. By registering it with ``name`` set to ``pprint``,
we will be able to reference this plugin as a new backend for the ``console`` setting.

Using the reporter backend
--------------------------

To use our newly registered reporter backend, it can either be specified in our ``.condarc`` configuration file:

.. code-block:: yaml

   console: pprint

Or, it can be specified at the command line using the ``--console`` option:

.. code-block:: bash

   conda info --envs --console=pprint

Further reading
===============

For detailed information on how to create a conda plugin from scratch, please see the following repository
which also contains a `cookiecutter <https://www.cookiecutter.io/>`_ recipe you can use to easily bootstrap
your project:

- `conda-plugins-template <https://github.com/conda/conda-plugin-template>`_

Below are relevant areas of the API docs for the reporter backends plugin hook:

- :class:`~conda.plugins.types.CondaReporterBackend` metadata object that must be returned from the reporter backends
  hook definition.
- :meth:`~conda.plugins.hookspec.CondaSpecs.conda_reporter_backends` hookspec definition for reporter backends which
  contains an example of its usage.
- :mod:`~conda.plugins.reporter_backends.console` our default implementation for the ``console`` reporter backend.
- :mod:`~conda.plugins.reporter_backends.json` our default implementation for the ``json`` reporter backend.
