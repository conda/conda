``conda env create``
********************
The `conda create` command is used to create a new conda environment with specified packages. It allows users to isolate different projects or workflows by creating separate environments with their own dependencies.

Usage
-----

The basic usage of the `conda create` command is as follows:

.. code-block:: console

    conda create [OPTIONS] [PACKAGE(S)]

Options
-------

The following options can be used with the `conda create` command:

.. code-block:: console

    -n, --name       Name of the environment to create.
    -p, --prefix     Full path to the environment location.
    --clone          Clone an existing environment.
    --file           Read package versions from the given file.
    --dev            Use the development version of the package.
    --freeze-installed
                     Do not update already-installed packages.

Examples
--------

1. Creating a new environment named "myenv" and installing specific packages:

.. code-block:: console

    conda create -n myenv python=3.10 numpy scipy

2. Creating an environment with a specific location:

.. code-block:: console

    conda create --prefix /path/to/myenv python=3.10 numpy tensorflow

3. Cloning an existing environment named "base" into a new environment named "myclone":

.. code-block:: console

    conda create --clone base -n myclone

4. Creating an environment from a file containing package specifications:

.. code-block:: console

    conda create --file requirements.txt

5. Creating a development environment with specific packages:

.. code-block:: console

    conda create --dev -n mydevenv numpy scipy

6. Creating an environment without updating already-installed packages:

.. code-block:: console

    conda create --freeze-installed -n myfrozenenv numpy scipy

Additional Information
----------------------

- For more advanced usage and options, refer to the official documentation: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#create-env-from-file

- It's recommended to use conda environments to manage package dependencies and isolate projects, ensuring reproducibility and avoiding conflicts between different projects.


.. argparse::
   :module: conda_env.cli.main
   :func: create_parser
   :prog: conda env
   :path: create
   :nodefault:
   :nodefaultconst:
