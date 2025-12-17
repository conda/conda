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

Conda includes several built-in health checks:

- **Missing Files** - Detects packages with missing files and can reinstall them
- **Altered Files** - Detects packages with modified files (checksum mismatch) and can reinstall them
- **Consistent Environment** - Checks for missing or inconsistent dependencies
- **Environment.txt** - Verifies the environment is registered in ``environments.txt``
- **Pinned File** - Validates the format of the ``pinned`` file
- **File Locking** - Reports if file locking is supported
- **REQUESTS_CA_BUNDLE** - Validates the SSL certificate bundle configuration

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: doctor
   :nodefault:
   :nodefaultconst:
