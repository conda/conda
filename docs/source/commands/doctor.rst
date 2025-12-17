``conda doctor``
****************

Display a health report for your environment by running registered health checks.

.. tip::

   ``conda check`` is an alias for ``conda doctor``. Use whichever you prefer!

Use ``conda doctor --fix`` to automatically fix issues that have available fixes.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: doctor
   :nodefault:
   :nodefaultconst:
