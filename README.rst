==============================
conda: package management tool
==============================

The ``conda`` command is the primary interface for managing an Anaconda installations. It can query and search the Anaconda package index and current Anaconda installation, create new Anaconda environments, and install and upgrade packages into existing Anaconda environments.


========
Examples
========

Create an Anaconda environment called ``myenv`` containing the latest version of scipy and all dependencies.

.. code-block:: bash

    $ conda create -n myenv scipy

Install the latest version of pandas into ``myenv``

.. code-block:: bash

    $ conda install -n myenv pandas

Update all specified packages to latest versions in ``myenv``

.. code-block:: bash

    $ conda update -n myenv anaconda

Now that you have a custom environment, there are two ways to make it available for use

**Using Activate**

Activating a conda environment is made simple through the use of the activate command

.. code-block:: bash

    $ source activate myenv

Similarly, to deactivate an environment and return your PATH variable to its previous state, use

.. code-block:: bash

    $ source deactivate
