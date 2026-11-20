``conda run``
*************

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: run
   :nodefault:
   :nodefaultconst:

Nested ``conda`` commands
=========================

On POSIX systems, an unqualified ``conda`` command currently resolves through
the invoking installation's shell function:

.. code-block:: console

   $ conda run -n target conda --version

This behavior is scheduled to change. In conda 27.9, ``conda`` will instead
resolve from the target environment's ``PATH``, like other executables.

Use an explicit form to avoid relying on behavior that will change:

.. code-block:: console

   # Use the invoking installation
   $ conda run -n target "$CONDA_EXE" --version

   # Use the target installation
   $ conda run -n target python -m conda --version
