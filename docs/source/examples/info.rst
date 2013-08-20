.. _info_example:

Info
----

``conda info`` provides information about Anaconda environments.

.. code-block:: bash

    $ conda info

    current conda install:

                 platform : osx-64
    conda command version : 1.8.2
           root directory : /Users/maggie/anaconda
           default prefix : /Users/maggie/anaconda
             channel URLs : http://repo.continuum.io/pkgs/dev/osx-64/
                            http://repo.continuum.io/pkgs/free/osx-64/
                            http://repo.continuum.io/pkgs/pro/osx-64/
              config file : /Users/maggie/.condarc

.. _envs_example:

``conda info --envs`` displays the **ROOT_DIR** Anaconda directory, and test environments within it.

.. code-block:: bash

    $ conda info -e
    # conda environments:
    #
    (root)                *  /Users/test/anaconda

``conda info --license`` displays information about local licenses, including what they are and where they can be located.

.. code-block:: bash

    $ conda info --license

    License directories:
        /Users/maggie/.continuum
        /Users/maggie/Library/Application Support/Anaconda
        /Users/maggie/anaconda/licenses
    License files (license*.txt):
    Package/feature end dates:

``conda info --system`` can be used to display the **PATH** and **PYTHONPATH** environment variables, which can be 
useful for the purposes of debugging.

.. code-block:: bash

  PATH: /Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda-test/bin:/Users/test/anaconda-test/bin:/Users/test/anaconda/bin:/usr/local/share/npm/bin:/usr/local/opt/coreutils/libexec/gnubin::/Users/test/bin:/Users/test/anaconda/bin:/usr/local/sbin:/usr/local/bin:/usr/local/share/python:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/sbin:/bin:/usr/X11R6/bin:/Users/test/hla
  PYTHONPATH: None
  DYLD_LIBRARY_PATH: None
  CONDA_DEFAULT_ENV: None

To display all relevant information at once, use the ``conda info --all` option.

.. code-block:: bash

    $ conda info --all

    Current conda install:

                 platform : osx-64
    conda command version : 1.8.2
           root directory : /Users/test/anaconda
           default prefix : /Users/test/anaconda
             channel URLs : http://repo.continuum.io/pkgs/dev/osx-64/
                            http://repo.continuum.io/pkgs/free/osx-64/
                            http://repo.continuum.io/pkgs/pro/osx-64/
              config file : /Users/test/.condarc

    # conda environments:
    #
    (root)                *  /Users/test/anaconda


    PATH: /Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda-test/bin:/Users/test/anaconda-test/bin:/Users/test/anaconda/bin:/usr/local/share/npm/bin:/usr/local/opt/coreutils/libexec/gnubin::/Users/test/bin:/Users/test/anaconda/bin:/usr/local/sbin:/usr/local/bin:/usr/local/share/python:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/sbin:/bin:/usr/X11R6/bin:/Users/test/hla
    PYTHONPATH: None
    DYLD_LIBRARY_PATH: None
    CONDA_DEFAULT_ENV: None

    License directories:
        /Users/test/.continuum
        /Users/test/Library/Application Support/Anaconda
        /Users/test/anaconda/licenses
    License files (license*.txt):
    Package/feature end dates: