======================
Environment Specifiers
======================

Conda can create environments from several file formats. Currently, conda natively
supports creating environments from:

* a yaml `environment.yaml`
* an "explicit" text file

For more information on how to manage conda environments, see the `Managing environments`_ documentation.

Example plugin
==============

The available readers can be extended with additional plugins via the ``conda_environment_specifiers``
hook.

.. hint::

   To see a fully functioning example of a Environment Spec backend,
   checkout the :mod:`~conda.env.specs.yaml_file` module.

.. autoapiclass:: conda.plugins.types.CondaEnvironmentSpeficier
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_environment_specifiers

Defining ``EnvSpecBase``
------------------------
The first class we define is a subclass of :class:`~conda.plugins.types.EnvSpecBase`. The
base class is an abstract base class which requires us to define our own implementations
of its abstract methods:

* ``can_handle`` Determines if the defined plugin can read and operate on the provided file.
* ``environment`` Expresses the provided environment file as a conda environment object.

.. hint::

   Be sure to be very specific when implementing the ``can_handle`` method. It should only
   return a ``True`` if the file can be parsed by the plugin. Making the ``can_handle``
   method too permissive in the types of files it handles may lead to conflicts with other plugins.

Registering the plugin hook
---------------------------
In order to make the plugin available to conda, it must be registered with the plugin
manager. Define a function with the ``plugins.hookimpl`` decorator to register
our plugin which returns our class wrapped in a
:class:`~conda.plugins.types.CondaEnvironmentSpecifier` object.

.. code-block:: python

   @plugins.hookimpl
   def conda_environment_specifiers():
       yield plugins.CondaEnvSpec(
           name="random",
           handler_class=RandomSpec,
       )

Using the Plugin
----------------
Once this plugin is registered, users will be able to create environments from the
types of files specified by the plugin. For example to create a `random` environment
using the plugin defined above:

.. code-block:: bash

   conda env create --file /doesnt/matter/any/way.random

.. _`Managing environments`:: https://pluggy.readthedocs.io/en/stable/
