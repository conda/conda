======================
Environment Specifiers
======================

Conda can create environments from several file formats. Currently, conda natively
supports creating environments from:

* A :ref:`YAML environment.yaml file <create-env-file-manually>`
* An :ref:`"explicit" text file <identical-conda-envs>`

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

Defining ``EnvironmentSpecBase``
--------------------------------

The first class we define is a subclass of :class:`~conda.plugins.types.EnvironmentSpecBase`. The
base class is an abstract base class which requires us to define our own implementations
of its abstract methods:

* ``can_handle`` Determines if the defined plugin can read and operate on the provided file.
* ``env`` Expresses the provided environment file as a conda environment object.

The class may also define the boolean class variable `detection_supported`. When set to
``True``, the plugin will be included in the environment spec type discovery process. Otherwise,
the plugin will only be able to be used when it is specifically selected. By default, this
value is ``True``.`

Be sure to be very specific when implementing the ``can_handle`` method. It should only
return a ``True`` if the file can be parsed by the plugin. Making the ``can_handle``
method too permissive in the types of files it handles may lead to conflicts with other
plugins. If multiple installed plugins are able to ``can_handle`` the same file type,
conda will return an error to the user.

Registering the plugin hook
---------------------------
In order to make the plugin available to conda, it must be registered with the plugin
manager. Define a function with the ``plugins.hookimpl`` decorator to register
our plugin which returns our class wrapped in a
:class:`~conda.plugins.types.CondaEnvironmentSpecifier` object. Note, that by default
autodetection is enabled.

.. code-block:: python

   @plugins.hookimpl
   def conda_environment_specifiers():
       yield plugins.CondaEnvSpec(
           name="random",
           environment_spec=RandomSpec,
       )

Using the Plugin
----------------
Once this plugin is registered, users will be able to create environments from the
types of files specified by the plugin. For example to create a `random` environment
using the plugin defined above:

.. code-block:: bash

   conda env create --file /doesnt/matter/any/way.random

Plugin detection
----------------

When conda is trying to determine which environment spec plugin to use it will loop through all
registered plugins and call their ``can_handle`` function. If one (and only one) plugin returns a
``True`` value, conda will use that plugin to read the provided environment spec. However, if multiple
plugins are detected an error will be raised.

Plugin authors may explicitly disable their plugin from being detected by disabling autodetection
in their plugin class

.. code-block:: python

    class RandomSpec(EnvironmentSpecBase):
        detection_supported = False

        def __init__(self, filename: str):
            self.filename = filename

        def can_handle(self):
            return True

        def env(self):
            return Environment(name="random-environment", dependencies=["python", "numpy"])

End users can bypass environment spec plugin detection and explicitly request a plugin to be used
by configuring conda to use a particular installed plugin. This can be done by either:

* cli by providing the ``--env-spec`` flag, or
* environment variable by setting the ``CONDA_ENV_SPEC`` environment variable, or
* ``.condarc`` by setting the ``environment_specifier`` config field

Another example plugin
-----------------------
In this example, we want to build a more realistic environemnt spec plugin. This
plugin has a scheme which expresses what it expects a valid environment file to
contain. In this example, a valid environment file is a ``.json`` file that defines:

* an environment name (required)
* a list of conda dependencies

.. code-block:: python

   import os
   from pydantic import BaseModel

   from conda.plugins import hookimpl
   from conda.plugins.types import CondaEnvironmentSpecifier, EnvironmentSpecBase
   from conda.env.env import Environment


   class MySimpleEnvironment(BaseModel):
       """An model representing an environment file."""

       # required
       name: str

       # optional
       conda_deps: list[str] = []


   class MySimpleSpec(EnvironmentSpecBase):
       def __init__(self, filename=None):
           self.filename = filename

       def _parse_data(self) -> MySimpleEnvironment:
           """ "Validate and convert the provided file into a MySimpleEnvironment"""
           with open(self.filename, "rb") as fp:
               json_data = fp.read()

           return MySimpleEnvironment.model_validate_json(json_data)

       def can_handle(self) -> bool:
           """
           Validates loader can process environment definition.
           This can handle if:
                 * the file exists
                 * the file can be read
                 * the data can be parsed as JSON into a MySimpleEnvironment object

           :return: True if the file can be parsed and handled, False otherwise
           """
           if not os.path.exists(self.filename):
               return False
           try:
               self._parse_data()
           except Exception:
               return False

           return True

       @property
       def env(self) -> Environment:
           """Returns the Environment representation of the environment spec file"""
           data = self._parse_data()
           return Environment(
               name=data.name,
               dependencies=data.conda_deps,
           )


   @hookimpl
   def conda_environment_specifiers():
       yield CondaEnvironmentSpecifier(
           name="mysimple",
           environment_spec=MySimpleSpec,
       )

We can test this out by trying to create a conda environment with a new file
that is compatible with the definied spec. Create a file ``testenv.json``

.. code-block::

   {
      "name": "mysimpletest",
      "conda_deps": ["numpy", "pandas"]
   }

Then, create the environment

.. code-block:: bash

   $ conda env create --file testenv.json
