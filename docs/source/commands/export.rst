``conda export``
****************

The ``conda export`` command allows you to export conda environments to various file formats.
This command supports an enhanced plugin-based architecture that supports multiple export formats for different use cases.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: export
   :nodefault:
   :nodefaultconst:

Overview
========

The export command creates portable representations of conda environments that can be shared
with others or used to recreate environments on different machines. The command supports
multiple output formats through a plugin architecture:

**Structured Formats** (cross-platform friendly):
  - ``environment-yaml`` - YAML format (default) [aliases: ``yaml``, ``yml``]
  - ``environment-json`` - JSON format [aliases: ``json``]

**Text Formats** (platform/architecture specific):
  - ``explicit`` - Explicit URLs with ``@EXPLICIT`` header (CEP 23 compliant)
  - ``requirements`` - Requirements format with MatchSpec strings [aliases: ``reqs``, ``txt``]

Format Selection
================

You can specify the export format in three ways:

1. **Explicit format specification** (recommended):

   .. code-block:: bash

      conda export --format=environment-yaml

2. **File extension detection**:

   .. code-block:: bash

      conda export --file=environment.yaml

3. **Default behavior** (outputs YAML to stdout):

   .. code-block:: bash

      conda export

Supported Output Formats
=========================

Environment YAML Format
------------------------

The default format that creates cross-platform compatible environment files.

+------------------+---------------------------+
| Format name      | ``environment-yaml``      |
+------------------+---------------------------+
| Aliases          | ``yaml``, ``yml``         |
+------------------+---------------------------+
| Auto-detected    | ``environment.yaml``,     |
| filenames        | ``environment.yml``       |
+------------------+---------------------------+

.. code-block:: bash

   # Export to stdout
   conda export --format=environment-yaml

   # Export to file
   conda export --file=environment.yaml

   # Alternative using aliases
   conda export --format=yaml
   conda export --format=yml

Example output:

.. code-block:: yaml

   name: myenv
   channels:
     - conda-forge
     - defaults
   dependencies:
     - numpy=2.3.1
     - pandas=2.3.1
     - python=3.13.5

Environment JSON Format
-----------------------

JSON representation of the environment for programmatic processing.

+------------------+---------------------------+
| Format name      | ``environment-json``      |
+------------------+---------------------------+
| Aliases          | ``json``                  |
+------------------+---------------------------+
| Auto-detected    | ``environment.json``      |
| filenames        |                           |
+------------------+---------------------------+

.. code-block:: bash

   # Export to stdout
   conda export --format=environment-json

   # Export to file
   conda export --file=environment.json

   # Alternative using alias
   conda export --format=json

Example output:

.. code-block:: json

   {
     "name": "myenv",
     "channels": [
       "conda-forge",
       "defaults"
     ],
     "dependencies": [
       "numpy=2.3.1",
       "pandas=2.3.1",
       "python=3.13.5"
     ]
   }

Explicit Format (CEP 23)
------------------------

Creates explicit package URLs for exact environment reproduction.

+------------------+---------------------------+
| Format name      | ``explicit``              |
+------------------+---------------------------+
| Aliases          | None                      |
+------------------+---------------------------+
| Auto-detected    | ``explicit.txt``          |
| filenames        |                           |
+------------------+---------------------------+

.. code-block:: bash

   # Export to stdout
   conda export --format=explicit

   # Export to file
   conda export --file=explicit.txt

Example output:

.. code-block:: text

   # This file may be used to create an environment using:
   # $ conda create --name <env> --file <this file>
   # platform: osx-arm64
   @EXPLICIT

   https://repo.anaconda.com/pkgs/main/noarch/tzdata-2025b-h04d1e81_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libffi-3.4.4-hca03da5_1.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libcxx-17.0.6-he5c5206_4.conda
   https://repo.anaconda.com/pkgs/main/noarch/pip-25.1-pyhc872135_2.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/pytz-2025.2-py313hca03da5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/python-3.13.5-h2eb94d5_100_cp313.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/ca-certificates-2025.2.25-hca03da5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/numexpr-2.11.0-py313hf08b1b5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/python_abi-3.13-0_cp313.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/bzip2-1.0.8-h80987f9_6.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/xz-5.6.4-h80987f9_1.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libgfortran5-11.3.0-h009349e_28.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/six-1.17.0-py313hca03da5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/blas-1.0-openblas.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libgfortran-5.0.0-11_3_0_hca03da5_28.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/openssl-3.0.17-h4ee41c1_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/wheel-0.45.1-py313hca03da5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/setuptools-72.1.0-py313hca03da5_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/numpy-base-2.3.1-py313h2506b34_0.conda
   https://repo.anaconda.com/pkgs/main/noarch/python-tzdata-2025.2-pyhd3eb1b0_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/llvm-openmp-17.0.6-h2f17746_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/numpy-2.3.1-py313h50dd0cd_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/bottleneck-1.4.2-py313ha35b7ea_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/ncurses-6.4-h313beb8_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/tk-8.6.14-h6ba3021_1.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/sqlite-3.50.2-h79febb2_1.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libmpdec-4.0.0-h80987f9_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/expat-2.7.1-h313beb8_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/readline-8.2-h1a28f6b_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/zlib-1.2.13-h18a0788_1.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/pandas-2.3.1-py313h17050e6_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/libopenblas-0.3.29-hea593b9_0.conda
   https://repo.anaconda.com/pkgs/main/osx-arm64/python-dateutil-2.9.0post0-py313hca03da5_2.conda

Requirements Format
-------------------

Creates a requirements file with MatchSpec strings.

.. warning::

   This format produces conda MatchSpec strings, which differ from ``conda list --export`` output.
   The requirements format includes full package specifications with channels and build strings,
   while ``conda list --export`` produces simpler package=version format suitable for basic reproduction.

+------------------+---------------------------+
| Format name      | ``requirements``          |
+------------------+---------------------------+
| Aliases          | ``reqs``, ``txt``         |
+------------------+---------------------------+
| Auto-detected    | ``requirements.txt``,     |
| filenames        | ``spec.txt``              |
+------------------+---------------------------+

.. code-block:: bash

   # Export to stdout
   conda export --format=requirements

   # Export to file
   conda export --file=requirements.txt

   # Alternative using aliases
   conda export --format=reqs
   conda export --format=txt

Example output:

.. code-block:: text

   # This file may be used to create an environment using:
   # $ conda create --name <env> --file <this file>
   # platform: osx-arm64
   # Note: This is a conda requirements file (MatchSpec format)
   # Contains conda package specifications, not pip requirements
   pkgs/main::blas==1.0=openblas
   pkgs/main::bottleneck==1.4.2=py313ha35b7ea_0
   pkgs/main::bzip2==1.0.8=h80987f9_6
   pkgs/main::ca-certificates==2025.2.25=hca03da5_0
   pkgs/main::expat==2.7.1=h313beb8_0
   pkgs/main::libcxx==17.0.6=he5c5206_4
   pkgs/main::libffi==3.4.4=hca03da5_1
   pkgs/main::libgfortran==5.0.0=11_3_0_hca03da5_28
   pkgs/main::libgfortran5==11.3.0=h009349e_28
   pkgs/main::libmpdec==4.0.0=h80987f9_0
   pkgs/main::libopenblas==0.3.29=hea593b9_0
   pkgs/main::llvm-openmp==17.0.6=h2f17746_0
   pkgs/main::ncurses==6.4=h313beb8_0
   pkgs/main::numexpr==2.11.0=py313hf08b1b5_0
   pkgs/main::numpy==2.3.1=py313h50dd0cd_0
   pkgs/main::numpy-base==2.3.1=py313h2506b34_0
   pkgs/main::openssl==3.0.17=h4ee41c1_0
   pkgs/main::pandas==2.3.1=py313h17050e6_0
   pkgs/main::pip==25.1=pyhc872135_2
   pkgs/main::python==3.13.5=h2eb94d5_100_cp313
   pkgs/main::python-dateutil==2.9.0post0=py313hca03da5_2
   pkgs/main::python-tzdata==2025.2=pyhd3eb1b0_0
   pkgs/main::python_abi==3.13=0_cp313
   pkgs/main::pytz==2025.2=py313hca03da5_0
   pkgs/main::readline==8.2=h1a28f6b_0
   pkgs/main::setuptools==72.1.0=py313hca03da5_0
   pkgs/main::six==1.17.0=py313hca03da5_0
   pkgs/main::sqlite==3.50.2=h79febb2_1
   pkgs/main::tk==8.6.14=h6ba3021_1
   pkgs/main::tzdata==2025b=h04d1e81_0
   pkgs/main::wheel==0.45.1=py313hca03da5_0
   pkgs/main::xz==5.6.4=h80987f9_1
   pkgs/main::zlib==1.2.13=h18a0788_1

Common Options
==============

Export Current Environment
---------------------------

Export the currently active environment:

.. code-block:: bash

   conda export

Export Specific Environment
----------------------------

Export a named environment:

.. code-block:: bash

   conda export --name myenv

Export Environment by Path
---------------------------

Export an environment by its path:

.. code-block:: bash

   conda export --prefix /path/to/env

Cross-Platform Compatibility
=============================

For cross-platform sharing, use the ``--from-history`` flag with structured formats:

.. code-block:: bash

   # Export only explicitly installed packages (cross-platform friendly)
   conda export --from-history --format=environment-yaml

   # This excludes dependency packages that might be platform-specific

When **not** to use ``--from-history``:
  - With ``explicit`` format (always uses all packages)
  - With ``requirements`` format (always uses all packages)
  - When you need exact dependency reproduction

Platform-Specific Exports
==========================

You can specify target platforms for export using the ``--platform`` option or by configuring
``export_platforms`` in your condarc file:

.. code-block:: bash

   # Export for specific platforms
   conda export --platform linux-64 --platform osx-64 --format=environment-yaml
   # or
   conda export --subdir linux-64 --subdir osx-64 --format=environment-yaml

   # Export using condarc configuration
   conda export --format=environment-yaml

With condarc configuration:

.. code-block:: yaml

   export_platforms:
     - linux-64
     - osx-64
     - win-64

File Format Detection
=====================

The command automatically detects the export format based on filename patterns:

.. list-table:: File Detection Patterns and Aliases
   :widths: 25 25 30 20
   :header-rows: 1

   * - Filename
     - Detected Format
     - Format Aliases
     - Description
   * - ``environment.yaml``
     - ``environment-yaml``
     - ``yaml``, ``yml``
     - YAML environment file
   * - ``environment.yml``
     - ``environment-yaml``
     - ``yaml``, ``yml``
     - YAML environment file (alternative extension)
   * - ``environment.json``
     - ``environment-json``
     - ``json``
     - JSON environment file
   * - ``explicit.txt``
     - ``explicit``
     - None
     - Explicit URL format
   * - ``requirements.txt``
     - ``requirements``
     - ``reqs``, ``txt``
     - Requirements format
   * - ``spec.txt``
     - ``requirements``
     - ``reqs``, ``txt``
     - Requirements format

You can use either the full format name or any of its aliases:

.. code-block:: bash

   # These are all equivalent
   conda export --format=environment-yaml
   conda export --format=yaml
   conda export --format=yml

   # These are all equivalent
   conda export --format=requirements
   conda export --format=reqs
   conda export --format=txt

Examples
========

Basic Usage
-----------

.. code-block:: bash

   # Export current environment to YAML (default)
   conda export > environment.yaml

   # Export specific environment
   conda export --name myenv --format=environment-yaml

   # Export with cross-platform compatibility
   conda export --from-history --file=environment.yaml

Advanced Usage
--------------

.. code-block:: bash

   # Export to explicit format for exact reproduction
   conda export --format=explicit --file=explicit.txt

   # Export to requirements format using aliases
   conda export --format=reqs > requirements.txt
   conda export --format=txt --file=spec.txt

   # Export YAML using short alias
   conda export --format=yml --file=environment.yml

   # Export JSON for programmatic processing
   conda export --format=json --file=environment.json

   # Export with custom channels
   conda export --channel conda-forge --format=environment-yaml

   # Export for multiple platforms
   conda export --platform linux-64 --platform osx-64 --format=environment-yaml
   conda export --subdir linux-64 --subdir osx-64 --format=environment-yaml

   # Export for specific platform only
   conda export --platform win-64 --format=explicit --file=explicit-win-64.txt
   conda export --subdir win-64 --format=explicit --file=explicit-win-64.txt

Error Handling
==============

The export command will fail in these cases:

- **Empty environments with text formats**: The ``explicit`` and ``requirements`` formats require installed packages
- **Unrecognized filenames**: Files that don't match supported patterns
- **Invalid format names**: Format names that don't exist

For unrecognized filenames, specify the format explicitly:

.. code-block:: bash

   # This will fail
   conda export --file=my-custom-file.xyz

   # This will work
   conda export --file=my-custom-file.xyz --format=environment-yaml

Plugin Architecture
===================

The export functionality is built on a plugin architecture that allows extending
conda with custom export formats. For information on creating custom exporters,
see :doc:`Environment Exporters <../dev-guide/plugins/environment_exporters>`.

See Also
========

- :doc:`conda env export <env/export>` - Traditional environment export command
- :doc:`Managing environments <../user-guide/tasks/manage-environments>` - Environment management guide
- :doc:`Environment Exporters <../dev-guide/plugins/environment_exporters>` - Plugin development guide
