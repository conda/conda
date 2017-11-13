============================
Using wheel files with conda
============================

Users sometimes have software in a
`Python wheel file <https://pythonwheels.com/>`_ and wish to use it with conda
or install it in a conda environment. There are three ways to do this.

The best way is to obtain the source code for the software and build a conda
package from the source and not from a wheel. This helps ensure that the new
package uses other conda packages to satisfy its dependencies.

The second best way is to build a conda package from the wheel file. This tells
conda more about the files present than a pip install. It is also less likely
than a pip install to cause errors by overwriting (or "clobbering") files.
Building a conda package from the wheel file also has the advantage that any
clobbering is more likely to happen at build time and not runtime.

The third way is to use pip to install a wheel file into a conda environment.
Some conda users do use this option safely. The first two ways are still the
safest and most reliable.


Building a conda package from a wheel file
==========================================

To build a conda package from a wheel file, install the .whl file in the conda
recipe's ``bld.bat`` or ``build.sh`` file.

You may download the .whl file in the source section of the conda recipe's
``meta.yaml`` file.

You may instead put the URL directly in the ``pip install`` command.

EXAMPLE: The conda recipe for TensorFlow has a ``pip install`` command in
`build.sh <https://github.com/conda/conda-recipes/blob/a796713805ac8eceed191c0cb475b51f4d00718c/python/tensorflow/build.sh#L7>`_
with the URL of a .whl file. The
`meta.yaml <https://github.com/conda/conda-recipes/blob/a796713805ac8eceed191c0cb475b51f4d00718c/python/tensorflow/meta.yaml>`_
file does not download or list the .whl file.

NOTE: It is important to ``pip install`` only the one desired package. Whenever
possible, install dependencies with conda and not pip.

We strongly recommend using the ``--no-deps`` option in the ``pip install``
command.
