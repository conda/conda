|

Here are mainly ``addons/changes`` for the nice ``conda: package management tool``. These are additional features I would like to see in the ``main conda package``. 
Hopefully one or the other idea makes it back to the original codebase and can be removed from here.


`For Installation see INSTALL.rst <INSTALL.rst>`_


ADDONS 
======

|

conda_recipes_dir
=================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_RECIPES_DIR:
    # directory in which conda recipes are located:
    # useful if one wants one common conda_recipes folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda_recipes)
    conda_recipes_dir: /home/0_CONDA_RELATED_0/conda-recipes


conda_repo_dir
=================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_REPO_DIR:
    # directory in which conda build packages are located: in the 
    # architecture subfolders
    # useful if one wants one common conda_repo folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda-bld)
    conda_repo_dir: /home/0_CONDA_RELATED_0/conda-repo


conda_sources_dir
=================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_REPO_DIR:
    # directory in which conda build packages are located: in the 
    # architecture subfolders
    # useful if one wants one common conda_repo folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda-bld)
    conda_repo_dir: /home/0_CONDA_RELATED_0/conda-repo


append build number to file
===========================

always append any build number  to the output package archive file


|
|
|

`For Installation see INSTALL.rst <INSTALL.rst>`_

peter1000: https://github.com/peter1000/
