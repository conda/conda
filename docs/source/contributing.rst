Contributing
============

.. _new-issues:

New Issues
----------

If your issue is a bug report or feature request for:

* **a specific conda package**: please file it at https://github.com/ContinuumIO/anaconda-issues/issues
* **anaconda.org**: please file it at https://github.com/Anaconda-Platform/support/issues
* **repo.anaconda.com**: please file it at https://github.com/ContinuumIO/anaconda-issues/issues
* **commands under** ``conda build``: please file it at https://github.com/conda/conda-build/issues
* **commands under** ``conda env``: please file it at https://github.com/conda/conda/issues
* **all other conda commands**: please file it at https://github.com/conda/conda/issues


Development Environment, Bash
-----------------------------

To set up an environment to start developing on conda code, we recommend the following steps:

1. Fork the conda/conda repository, clone it locally anywhere you choose (an isolation miniconda
   will be set up within the clone directory), and set up ``git remote`` to point to upstream
   and fork. For detailed directions, see below.

 1a. Choose where you want the repository located (not location of existing conda)

  .. code-block :: console

       CONDA_PROJECT_ROOT="$HOME/conda"

 1b. Clone the project, with ``upstream`` being the main repository. Make sure to click the ``Fork``
 button above so you have your own copy of this repo.

    .. code-block :: console

       GITHUB_USERNAME=kalefranz
       git clone git@github.com:$GITHUB_USERNAME/conda "$CONDA_PROJECT_ROOT"
       cd "$CONDA_PROJECT_ROOT"
       git remote --add upstream git@github.com:conda/conda

2. Create a local development environment, and activate that environment

  .. code-block :: console

       . dev/start

  This command will create a project-specific base environment at ``./devenv``. If
  the environment already exists, this command will just quickly activate the
  already-created ``./devenv`` environment.

  To be sure that the conda code being interpreted is the code in the project directory,
  look at the value of ``conda location:`` in the output of ``conda info --all``.

3. Run conda's unit tests using GNU make

  .. code-block :: console

       make unit

 or alternately with pytest

  .. code-block :: console

       py.test -m "not integration and not installed" conda tests

 or you can use pytest to focus on one specific test

  .. code-block :: console

       py.test tests/test_create.py -k create_install_update_remove_smoketest



Development Environment, Windows cmd.exe shell
----------------------------------------------

In these steps, we assume ``git`` is installed and available on ``PATH``.

1. Choose where you want the project located

  .. code-block :: console

       set "CONDA_PROJECT_ROOT=%HOMEPATH%\conda"

2. Clone the project, with ``origin`` being the main repository. Make sure to click the ``Fork``
   button above so you have your own copy of this repo.

  .. code-block :: console

       set GITHUB_USERNAME=kalefranz
       git clone git@github.com:conda/conda "%CONDA_PROJECT_ROOT%"
       cd "%CONDA_PROJECT_ROOT%"
       git remote --add %GITHUB_USERNAME% git@github.com:%GITHUB_USERNAME%/conda

 To be sure that the conda code being interpreted is the code in the project directory,
 look at the value of ``conda location:`` in the output of ``conda info --all``.

3. Create a local development environment, and activate that environment

  .. code-block :: console

       .\dev\start

 This command will create a project-specific base environment at ``.\devenv``. If
 the environment already exists, this command will just quickly activate the
 already-created ``.\devenv`` environment.


Conda Contributor License Agreement
-----------------------------------

In case you're new to CLAs, this is rather standard procedure for larger projects.
`Django <https://www.djangoproject.com/foundation/cla/>`_ and even
`Python <https://www.python.org/psf/contrib/contrib-form/>`_ itself both use something similar.

.. raw:: html

    <iframe src="https://secure.na2.echosign.com/public/esignWidget?wid=CBFCIBAA3AAABLblqZhAilb-zm-tOgZP_zBG3ZHOog9hmJP4V_P62z2GudnNBb6CviTDQ8MbXciYDiBNF9G4*&hosted=false" width="100%" height="100%" frameborder="0" style="border: 0; overflow: hidden; min-height: 500px; min-width: 600px;"></iframe>
