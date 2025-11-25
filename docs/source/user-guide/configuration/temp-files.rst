=======================================
Configuring Temporary File Locations
=======================================

Conda creates various temporary files during its operations. You can control where these temporary files are stored using standard operating system environment variables.

.. contents:: On this page
   :local:
   :depth: 2

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

Conda respects the standard operating system environment variables for temporary file locations. Python's ``tempfile`` `module <https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir>`_, which conda uses internally, checks these variables in the following order on **all platforms**:

1. ``TMPDIR``
2. ``TEMP``
3. ``TMP``

If none of these environment variables are set, Python falls back to platform-specific default locations:

* **Windows**: ``C:\TEMP``, ``C:\TMP``, ``\TEMP``, ``\TMP`` (in that order), then ``C:\Windows\Temp``
* **Unix/Linux/macOS**: ``/tmp``, ``/var/tmp``, ``/usr/tmp`` (in that order)
* **All platforms**: As a last resort, the current working directory

Setting temporary directories
==============================

**Unix/Linux/macOS:**

.. code-block:: bash

   # For current session
   export TMPDIR=/path/to/writable/tmp
   mkdir -p $TMPDIR

   # To make permanent, add to ~/.bashrc, ~/.bash_profile, or equivalent shell profile file
   echo 'export TMPDIR=/path/to/writable/tmp' >> ~/.bashrc

   # For a single command
   TMPDIR=/path/to/writable/tmp conda install package_name

**Windows:**

.. code-block:: bat

   # For current session (Command Prompt)
   set TEMP=C:\path\to\writable\tmp
   md %TEMP%

   # For current session (PowerShell)
   $env:TEMP = "C:\path\to\writable\tmp"
   New-Item -ItemType Directory -Path $env:TEMP -Force

   # To make permanent, use the System Properties dialog:
   # - Edit the system environment variables or
   # - Edit environment variables for your account

Temporary files created by conda
=================================

Conda creates temporary files in the following situations:

Activation and execution scripts
---------------------------------

* **conda activate**: Creates temporary shell scripts to set up the environment
* **conda run**: Creates temporary wrapper scripts to execute commands in an environment

These scripts are automatically cleaned up after use (unless ``CONDA_TEST_SAVE_TEMPS`` is set for debugging).

Package installation
--------------------

* **Pip integration**: Creates temporary ``requirements.txt`` files when installing pip dependencies from environment files
* **Python compilation**: Creates temporary files when compiling ``.py`` files to ``.pyc`` bytecode

System operations
-----------------

* **Windows Unicode handling**: Creates temporary batch files for directory operations with Unicode paths
* **Windows elevated permissions**: Creates temporary JSON files when running with administrator privileges
* **Package extraction**: Uses temporary directories when extracting package archives
* **Repodata operations**: Creates temporary cache files during repository data updates

.. note::
   Package downloads and extracted package caches (in ``pkgs_dirs``) are **not** temporary files—they are persistent caches. To configure their location, see :doc:`custom-env-and-pkg-locations`.

Examples
========

Container/Docker environments
-----------------------------

When running conda in a container where the default ``/tmp`` might be small or read-only:

.. code-block:: dockerfile

   FROM continuumio/miniconda3

   # Set temporary directory to a writable location with more space
   ENV TMPDIR=/opt/conda/tmp
   RUN mkdir -p /opt/conda/tmp

HPC/shared computing
--------------------

On HPC systems, you might want to use scratch space:

.. code-block:: bash

   # In your job script or ~/.bashrc
   export TMPDIR=$SCRATCH/tmp
   mkdir -p $TMPDIR

Limited disk space
------------------

If your home directory has limited space but you have access to another volume:

.. code-block:: bash

   # Create temporary directory on larger volume
   mkdir -p /mnt/large-volume/tmp

   # Set for all future sessions
   echo 'export TMPDIR=/mnt/large-volume/tmp' >> ~/.bashrc

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
