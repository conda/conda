=================================
Build scripts (build.sh, bld.bat)
=================================

The ``build.sh`` file is the build script for Linux and macOS and ``bld.bat``
is the build script for Windows. These scripts contain the logic that carries
out your build steps. Traditionally it has also included install steps. With
the traditional one-package-per-recipe way of doing things, anything that your
build script copies into the ``$PREFIX`` or ``%PREFIX%`` folder will be
included in your output package. For example, this ``build.sh``:

.. code-block:: bash

  mkdir -p $PREFIX/bin
  cp $RECIPE_DIR/my_script_with_recipe.sh $PREFIX/bin/super-cool-script.sh

If you don't care about deploying your package with pip on PyPI, this can save
you a lot of time in figuring out the proper way to include additional files
with setup.py.

There are many environment variables defined for you to use in build.sh and
bld.bat. Please see :ref:`env-vars` for more information.

As of conda-build 2.1, you can also define multiple output packages. Each
package has its own script or list of files to include. The rules for these
outputs are documented at :ref:`package-outputs`. When any output is defined,
this overrides the default behavior of bundling anything in ``$PREFIX``. So
to output multiple packages from a single recipe, remove any installation steps
from ``build.sh`` or ``bld.bat`` and do them instead in your install script(s)
for each output.

``build.sh`` and ``bld.bat`` are optional. You can instead use the
``build/script`` key in your ``meta.yaml``, with each value being either a
string command or a list of string commands. Any commands you put there must be
able to run on every platform for which you build. For example, you can't use
the ``cp`` command because cmd.exe won't understand it in Windows.

``build.sh`` is run with ``bash`` and ``bld.bat`` is run with ``cmd.exe``.

There is some development towards the ability to use bash scripts in Windows,
but this is not currently supported.
