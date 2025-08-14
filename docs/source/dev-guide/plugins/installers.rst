==========
Installers
==========

Conda can install multiple types of packages. Natively, conda
support installing conda packages (``.tar.bz2`` and ``.conda``).
The installer plugin interface allows users to extend conda to
install new types of packages. Packages installed by installer
plugins might not support all the features of the native conda
packages.

Example plugin
==============

The available installers can be extended with additional plugins
via the ``conda_installers``hook.

.. autoapiclass:: conda.plugins.types.CondaInstaller
   :members:
   :undoc-members:


The following code code-block shows how to define a new installer
plugin, called ``MyPipInstaller``. This plugin will install packages
using pip.

.. code-block:: python

    import sys
    from subprocess import run
    from conda import plugins
    from conda.plugins.types import CondaInstaller, InstallerBase

    python = sys.executable


    class MyPipInstaller(InstallerBase):
        def __init__(self, **kwargs):
            pass

        def install(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
            return ["installing {specs} into {prefix}"]

        def dry_run(self, prefix, specs, *args, **kwargs) -> Iterable[str]:
            return ["DRYRUN: installing {specs} into {prefix}"]


    @plugins.hookimpl
    def conda_installers():
        yield CondaInstaller(
            name="pip",
            types=["pip"],
            installer=MyPipInstaller,
        )

Defining ``InstallerBase``
--------------------------
The first class we define is a subclass of :class:`~conda.plugins.types.InstallerBase`.
The base class is an abstract base class which requires us to define
our own implementations of its abstract methods:

* ``install`` Given a list of specs and a prefix, install the specs into the prefix.
* ``dry_run`` Given a list of specs and a prefix, return a list of strings of the actions that would have run during an install.


Registering the plugin hook
---------------------------
In order to make the plugin available to conda, it must be registered with the plugin
manager. Define a function with the ``plugins.hookimpl`` decorator to register
our plugin which returns our class wrapped in a
:class:`~conda.plugins.types.CondaInstaller` object.
