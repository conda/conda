``conda doctor``
****************

Display a health report for your environment by running registered health checks.

.. tip::

   ``conda check`` is an alias for ``conda doctor``. Use whichever you prefer!

Fixing Issues
=============

Use ``conda doctor --fix`` to automatically fix issues that have available fixes.
When a health check detects a problem and has an associated fix, the ``--fix`` flag
will attempt to repair it.

By default, fixes will prompt for confirmation before making changes. Use
``--yes`` to skip confirmation prompts, or ``--dry-run`` to see what would
be changed without actually making modifications.

Example::

   # Check environment health
   conda doctor

   # Fix issues automatically (with confirmation prompts)
   conda doctor --fix

   # Fix issues without prompts
   conda doctor --fix --yes

   # Preview fixes without applying them
   conda doctor --fix --dry-run

Built-in Health Checks
======================

Use ``conda doctor --list`` to see all available health checks and their fix capabilities.
Conda includes several built-in health checks:

- ``missing-files`` - Detects packages with missing files and can reinstall them
- ``altered-files`` - Detects packages with modified files (checksum mismatch) and can reinstall them
- ``consistency`` - Checks for missing or inconsistent dependencies
- ``environment-txt`` - Verifies the environment is registered in ``environments.txt``
- ``pinned`` - Validates the format of the ``pinned`` file
- ``file-locking`` - Reports if file locking is supported
- ``requests-ca-bundle`` - Validates the SSL certificate bundle configuration

You can run specific health checks by name::

   conda doctor missing-files altered-files

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: doctor
   :nodefault:
   :nodefaultconst:
