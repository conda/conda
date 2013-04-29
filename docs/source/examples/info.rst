.. _info_example:

Info
----

``conda info`` provides information about anaconda environments.

.. code-block:: bash

    $ conda info

    Current Anaconda install:


             platform : osx-64
    conda command version : 1.5.1
       root directory : /Users/test/anaconda
       default prefix : /Users/test/anaconda
         channel URLs : http://repo.continuum.io/pkgs/free/osx-64/
                        http://repo.continuum.io/pkgs/pro/osx-64/
    environment locations : /Users/test/anaconda/envs
          config file : None

.. _envs_example:

``conda info --envs`` displays the ROOT_DIR anaconda directory, and test environments within it.

.. code-block:: bash

    $ conda info -e
    Known Anaconda environments:

        /Users/test/anaconda
        /Users/test/anaconda/envs/test

.. _locations_example:

``conda info --locations`` displays the places `conda` will look for anaconda environments.  There is
a default environment at ``ROOT_DIR/envs``.

.. code-block:: bash

    $ conda info --locations

    Locations for Anaconda environments:

        /Users/test/anaconda/envs  (system location)

It is possible to add additional locations :ref:`by editing .condarc <config>`.  

Here is an example
of what will be displayed if additional locations have been created.

.. code-block:: bash

    $ conda info --locations

    Locations for Anaconda environments:

        /Users/test/anaconda/envs  (system location) 
        /Users/test/envs

``conda info --license`` displays information about local licenses, including what they are and where they can be located.

.. code-block:: bash

    $ conda info --license

    License directories:
      /Users/maggie/.continuum
      /Users/maggie/Library/Application Support/Anaconda
      /Users/maggie/anaconda/licenses
    License files (license*.txt):
      /Users/maggie/.continuum/license_iopro_20130424125413.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'IOPro'
                             packages : u'iopro'
                             end_date : u'2014-04-24'
                                 type : None
  Package/feature end dates:
      iopro           : 2014-04-24

``conda info --system`` can be used to display the PATH and PYTHONPATH environment variables, which can be 
useful for the purposes of debugging.

.. code-block:: bash

  PATH: /usr/local/share/npm/bin:/usr/local/opt/coreutils/libexec/gnubin::/Users/test/bin:/Users/test/anaconda/bin:/usr/local/sbin:/usr/local/bin:/usr/local/share/python:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/sbin:/bin:/usr/X11R6/bin:/Users/test/hla
  PYTHONPATH: None
  DYLD_LIBRARY_PATH: None
  CONDA_DEFAULT_ENV: None

To display all relevant information at once, use the ``conda info --all` option.

.. code-block:: bash

    $ conda info --all

  Current conda install:

               platform : osx-64
  conda command version : 1.5.1
         root directory : /Users/test/anaconda
         default prefix : /Users/test/anaconda
           channel URLs : http://repo.continuum.io/pkgs/free/osx-64/
                          http://repo.continuum.io/pkgs/pro/osx-64/
  environment locations : /Users/test/anaconda/envs
            config file : None


  Locations for conda environments:

      /Users/test/anaconda/envs  (system location)

  Known conda environments: None

  PATH: /usr/local/share/npm/bin:/usr/local/opt/coreutils/libexec/gnubin::/Users/test/bin:/Users/test/anaconda/bin:/usr/local/sbin:/usr/local/bin:/usr/local/share/python:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/sbin:/bin:/usr/X11R6/bin:/Users/test/hla
  PYTHONPATH: None
  DYLD_LIBRARY_PATH: None
  CONDA_DEFAULT_ENV: None

  License directories:
      /Users/test/.continuum
      /Users/test/Library/Application Support/Anaconda
      /Users/test/anaconda/licenses
  License files (license*.txt):
      /Users/test/.continuum/license_iopro_20130424125413.txt
                 Reading license file : 1
                      Signature valid : 1
                         Vendor match : 1
                              product : u'IOPro'
                             packages : u'iopro'
                             end_date : u'2014-04-24'
                                 type : None
  Package/feature end dates:
      iopro           : 2014-04-24