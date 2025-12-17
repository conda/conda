``conda doctor``
****************

Display a health report for your environment by running registered health checks.

.. tip::

   ``conda check`` is an alias for ``conda doctor``. Use whichever you prefer!

   The ``check`` alias pairs well with ``conda fix`` for diagnosing and repairing
   environment issues.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: doctor
   :nodefault:
   :nodefaultconst:
