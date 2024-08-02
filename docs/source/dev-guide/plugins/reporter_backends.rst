=================
Reporter Backends
=================

A reporter backend is a plugin hook that allows you to change the output displayed
for existing conda commands. Internally, conda uses this to differentiate between
displaying normal, "console" output or displaying "json" output. An example of each
of these reporter backend types is shown below:

.. code-block:: shell

   # "console" output
   conda info --envs

   # conda environments:
   #
   base                     * /home/user/conda/
   env-1                      /home/user/.conda/envs/env-1

   # "json" output (output has been truncated)
   conda info --envs --json
   {
   ...
     "envs": [
       "/home/user/conda/",
       "/home/user/.conda/envs/env-1"
     ]
   ...
   }

Via its plugins system, conda allows you to define entirely new reporter backends. This gives
you an extreme amount of flexibility when it comes to modifying how conda looks
and feels. The first step to doing this is by creating your own subclass of
:class:`~conda.plugins.types.ReporterRendererBase`. You then register it by using the
``conda_reporter_backends`` hook.

For information on configuring and using these reporter backends in conda itself see:

- :ref:`Settings: reporters <reporters>`

Example plugin
==============

The following example defines a simple plugin which uses the :func:`~pprint.pformat` function for rendering
parts of conda's output:

.. code-block:: python

    from pprint import pformat

    from conda import plugins
    from conda.plugins.types import (
        CondaReporterBackend,
        ReporterRendererBase,
        ProgressBarBase,
    )


    class PprintReporterRenderer(ReporterRendererBase):
        """ "
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
:class:`~conda.plugins.types.ReporterRendererBase`. The base class is an abstract base class which requires us
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
we will be able to reference this plugin in the ``reporters`` section of our configuration:

.. code-block:: yaml

   reporters:
     - backend: pprint
       output: stdout

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
