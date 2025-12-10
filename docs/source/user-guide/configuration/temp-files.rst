=======================================
Configuring Temporary File Locations
=======================================

Conda creates various temporary files during its operations. You can control where these temporary files are stored using standard operating system environment variables.

Why configure temporary file locations?
========================================

You may need to configure temporary file locations when:

* Default temporary directories have limited disk space
* Default locations are read-only (common in containers, HPC environments, or restrictive permissions)
* Compliance requirements mandate temporary files be stored in specific locations
* Performance considerations (e.g., using faster storage for temporary operations)
* Working in multi-user or shared computing environments

Environment variables
=====================

Conda respects the standard operating system environment variables for temporary file locations. Python's :py:mod:`tempfile` module (specifically :py:func:`tempfile.gettempdir`), which conda uses internally, checks these variables in the following order on **all platforms**:

1. ``TMPDIR``
2. ``TEMP``
3. ``TMP``

If none of these environment variables are set, Python falls back to platform-specific default locations:

* **Windows**: ``C:\TEMP``, ``C:\TMP``, ``\TEMP``, ``\TMP`` (in that order)
* **Unix/Linux/macOS**: ``/tmp``, ``/var/tmp``, ``/usr/tmp`` (in that order)
* **All platforms**: As a last resort, the current working directory

Setting temporary directories
==============================

**Unix/Linux/macOS:**

.. code-block:: bash

   # For current session
   export TMPDIR=/path/to/writable/tmp
   mkdir -p $TMPDIR

   # To make permanent, add to ~/.bashrc or equivalent shell profile file
   echo 'export TMPDIR=/path/to/writable/tmp' >> ~/.bashrc

   # For a single command
   TMPDIR=/path/to/writable/tmp conda install package_name

**Windows:**

.. code-block:: bat

   REM For current session (Command Prompt)
   set TEMP=C:\path\to\writable\tmp
   md %TEMP%

.. code-block:: powershell

   # For current session (PowerShell)
   $env:TEMP = "C:\path\to\writable\tmp"
   New-Item -ItemType Directory -Path $env:TEMP -Force

   # To make permanent, use the System Properties dialog:
   # - Edit the system environment variables or
   # - Edit environment variables for your account

**Container/Docker environments:**

In your ``Dockerfile`` or ``docker-compose.yml``:

.. code-block:: dockerfile

   FROM continuumio/miniconda3

   # Set temporary directory to a writable location with more space
   ENV TMPDIR=/opt/conda/tmp
   RUN mkdir -p /opt/conda/tmp

Verifying temporary directory location
=======================================

To check where conda will create temporary files, use ``conda info``:

.. code-block:: bash

   conda info

Look for the ``temporary directory`` line in the output, which shows the currently configured temporary directory location.

Alternatively, you can check directly with Python:

.. code-block:: bash

   python -c "import tempfile; print(tempfile.gettempdir())"

This will show you the directory that Python (and therefore conda) will use for temporary files.

See also
========

* :ref:`temp-file-errors` - Troubleshooting temporary file errors (permission denied, read-only filesystem, no space left on device)
* :doc:`custom-env-and-pkg-locations` - Configure locations for environments and package cache
* :doc:`settings` - Complete list of conda configuration settings
