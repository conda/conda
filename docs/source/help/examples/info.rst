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

``conda info --license`` displays information about local licenses, including what they are and where they are located.

.. code-block:: bash

    $ conda info --license

  License directories:
      /Users/test/.continuum
      /Users/test/Library/Application Support/Anaconda
      /Users/test/anaconda/licenses
  License files (license*.txt):
      /Users/test/.continuum/license_academic_20130819112706.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'Academic'
                             packages : u'numbapro mkl iopro'
                             end_date : u'2014-08-19'
                                 type : None
      /Users/test/.continuum/license_accelerate_20130819111836.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'Accelerate'
                             packages : u'numbapro mkl'
                             end_date : u'2014-08-19'
                                 type : None
      /Users/test/.continuum/license_iopro_20130819111946.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'IOPro'
                             packages : u'iopro'
                             end_date : u'2014-08-19'
                                 type : None
      /Users/test/.continuum/license_mkl_optimizations_20130819111914.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'MKL_Optimizations'
                             packages : u'mkl'
                             end_date : u'2014-08-19'
                                 type : None
  Package/feature end dates:
      numbapro        : 2014-08-19
      iopro           : 2014-08-19
      mkl             : 2014-08-19

``conda info --system`` can be used to display the **PATH** and **PYTHONPATH** environment variables, which can be
useful for the purposes of debugging.

.. code-block:: bash

  PATH: /Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin: ... /Users/test/hla
  PYTHONPATH: None
  DYLD_LIBRARY_PATH: None
  CONDA_DEFAULT_ENV: None

To display all relevant information at once, use the ``conda info --all`` option.

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


    PATH: /Users/test/anaconda/bin:/Users/test/anaconda/bin:/Users/test/anaconda/bin: ... /Users/test/hla
    PYTHONPATH: None
    DYLD_LIBRARY_PATH: None
    CONDA_DEFAULT_ENV: None

    License directories:
        /Users/test/.continuum
        /Users/test/Library/Application Support/Anaconda
        /Users/test/anaconda/licenses
    License files (license*.txt):
    Package/feature end dates:
