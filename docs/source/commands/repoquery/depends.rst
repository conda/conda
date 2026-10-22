``conda repoquery depends``
***************************

.. note::
   The ``conda repoquery depends`` command is provided by the ``conda-libmamba-solver``.
   For more information on the subcommands provided, see
   `Subcommands <https://conda.github.io/conda-libmamba-solver/user-guide/subcommands/>`_.

   For more information on the libmamba solver, see
   :doc:`Solvers <../../user-guide/concepts/solvers>`.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: repoquery depends
   :nodefault:
   :nodefaultconst:
