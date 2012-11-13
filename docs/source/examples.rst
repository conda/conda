==================
Examples
==================

Below are a few examples using conda commands with a variety of optional arguments.

-------------------
Getting Information
-------------------

.. _info_example:

Info
----

``conda info`` provides information about anaconda environments.

.. code-block:: bash

    $ conda info

    Current Anaconda install:

                   target : pro
                 platform : osx-64
    conda command version : 1.1.0
           root directory : /Users/test/anaconda
       packages directory : /Users/test/anaconda/pkgs
          repository URLS : ['http://repo.continuum.io/pkgs/osx-64/']
    environment locations : ['/Users/test/anaconda/envs']


.. _list_example:

List
----

``conda list -p`` shows the activated packages and their versions in a specific 
environment directory. ``--prefix`` also works.  If no prefix is provided,
conda will look in the default environment.

.. code-block:: bash

    $ conda list -p ~/envs/test2
    nose                      1.1.2
    numpy                     1.6.2
    python                    2.7.3
    readline                  6.2
    sqlite                    3.7.13
    zlib                      1.2.7

In this next example, we leave off the prefix and search for packages starting with ``py`` in the default directory.

.. code-block:: bash

    $ conda list ^py
    packages and versions matching the expression '^py' in environment at /Users/test/anaconda:
    py                        2.4.12
    pyaudio                   0.2.6
    pycurl                    7.19.0
    pyflakes                  0.5.0
    pygments                  1.5
    pysal                     1.4.0
    pysam                     0.6
    pyside                    1.1.2
    pytables                  2.4.0
    pytest                    2.3.3
    python                    2.7.3
    python.app                1.0
    pytz                      2012d
    pyyaml                    3.10
    pyzmq                     2.2.0.1


.. _search_example:

Search
------

``conda search`` is a versatile conda option that can be used in a variety of ways.

In the first example, we want to simply search for scipy and see if it is in
conda's list of packages.  We will also show its dependencies.

.. code-block:: bash

    $ conda search -s scipy
    12 matches found:

       package: scipy-0.11.0rc2 [pro]
          arch: x86_64
      filename: scipy-0.11.0rc2-np16py26_pro0.tar.bz2
           md5: 177898fbbd82196f066968ff03079a1d
      requires:
            numpy-1.6
            python-2.6

       ...

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np17py27_pro0.tar.bz2
           md5: f4cbc54250e4c3d18ab04b60c6fe9f17
      requires:
            numpy-1.7
            python-2.7

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np16py26_pro0.tar.bz2
           md5: 009960638acadf845f1249f1f3888e18
      requires:
            numpy-1.6
            python-2.6

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np15py27_pro0.tar.bz2
           md5: 7a7ce190a0a221af74b89183687d1a5b
      requires:
            numpy-1.5
            python-2.7

In this next example, we will refine our search a bit.  With ``^l.*py$`` we want to find any packages
that begin with ``l`` followed by any number of characters, and ending with ``py``.

.. code-block:: bash

    $ conda search -s ^l.*py$
    6 matches found:

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py27_0.tar.bz2
           md5: 3d154f02354b22ac2e0ad76e73073f4e
      requires:
            llvm-3.1
            python-2.7

       package: llvmpy-0.8.3.dev 
          arch: x86_64
      filename: llvmpy-0.8.3.dev-py26_0.tar.bz2
           md5: 6cebbf5e402a9c5a6d3fba29182f980d
      requires:
            llvm-3.1
            python-2.6

        ...

       package: llvmpy-0.8.4.dev 
          arch: x86_64
      filename: llvmpy-0.8.4.dev-py27_0.tar.bz2
           md5: ce8b92705249d638850528bdddc27dc8
      requires:
            llvm-3.1
            python-2.7

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py26_0.tar.bz2
           md5: d0edc507d66dd34e32dc9d277c68fe36
      requires:
            llvm-3.1
            python-2.6



While the previous examples have illustrated conda's basic usefulness, they have only scratched
the surface of what this option can do.

For this example, we will use an environment containing scipy=0.11.0, numpy=1.7, python=2.7 and their dependencies.
Using the prefix option (``-p``), we can select an environment, and search for all packages that are compatible with it.

.. code-block:: bash

    $ conda search -p ~/anaconda/envs/onlyScipy/

       package: anaconda-1.1 [ce]
          arch: x86_64
      filename: anaconda-1.1-np17py27_ce0.tar.bz2
           md5: 1eda25b89e4a6ec9293840e07f2aa89b

       package: anaconda-1.1.4 [pro]
          arch: x86_64
      filename: anaconda-1.1.4-np15py26_pro0.tar.bz2
           md5: c38095a04aeca3838c622b86c632235d

       package: anaconda-1.1 [pro]
          arch: x86_64
      filename: anaconda-1.1-np15py26_pro0.tar.bz2
           md5: 683498ea22ca6675b7f1281c9dc62bb3

       package: anaconda-1.1.4 [pro]
          arch: x86_64
      filename: anaconda-1.1.4-np17py27_pro0.tar.bz2
           md5: e53725e6c03427c8445cc966a0b877d3


    ...

    ackage: wakaridata-1.0 
          arch: x86_64
      filename: wakaridata-1.0-py26_0.tar.bz2
           md5: 36e06413d215e9db75ffda561ecd6642

       package: wakaridata-1.0 
          arch: x86_64
      filename: wakaridata-1.0-py27_0.tar.bz2
           md5: 5df6f71c1764ab83c3c82e589fd84092

       package: werkzeug-0.8.3 
          arch: x86_64
      filename: werkzeug-0.8.3-py27_0.tar.bz2
           md5: 0e0775f16145096081f0ff2c60e7334e

       package: werkzeug-0.8.3 
          arch: x86_64
      filename: werkzeug-0.8.3-py26_0.tar.bz2
           md5: aff1d6a44c922e3f9a27ae35949b6866

       package: wiserf-0.9 
          arch: x86_64
      filename: wiserf-0.9-np17py27_0.tar.bz2
           md5: 8a6c5c81248c3fa68c9197c7f5742245

       package: yaml-0.1.4 
          arch: x86_64
      filename: yaml-0.1.4-0.tar.bz2
           md5: 8d576ab603ce38ef619d59f71875e8d7

       package: zeromq-2.2.0 
          arch: x86_64
      filename: zeromq-2.2.0-0.tar.bz2
           md5: 992590aa055cb67c00e8460e81ae49f8

       package: zlib-1.2.7 
          arch: x86_64
      filename: zlib-1.2.7-0.tar.bz2
           md5: 0841a23e33e22d0b139620dc47a37223


.. _depends_example:

Depends
-------

By default ``conda depends`` will simply display all dependencies
for a given package.

.. code-block:: bash

    $ conda depends numpy
    numpy depends on the following packages:
        nose 1.1.2
        python 2.7
        readline 6.2
        sqlite 3.7.13
        zlib 1.2.7

Running ``conda depends`` with the reverse dependency command shows all packages that require numpy.

.. code-block:: bash

    $ conda depends -r numpy
    The following activated packages depend on numpy:
        h5py-2.0.1
        iopro-1.1.0
        matplotlib-1.1.1
        numba-0.1.1
        numbapro-0.6
        numexpr-2.0.1
        pandas-0.8.1
        pysal-1.4.0
        pytables-2.4.0
        scikit-learn-0.11
        scikits-image-0.6.1
        scipy-0.11.0
        statsmodels-0.4.3
        wiserf-0.9

Using reverse dependency in addition to the verbose (``-v``) and ``no-prefix`` commands offers
more information and includes packages that depend on any version of numpy.

.. code-block:: bash

    $ conda depends --no-prefix -rv numpy
    The following packages depend on numpy:
        chaco-4.2.1.dev-np17py27_0
        h5py-2.0.1-np17py26_0
        h5py-2.0.1-np17py27_0
        h5py-2.1.0-np17py26_0
        h5py-2.1.0-np17py27_0

        ....

        statsmodels-0.4.3-np16py26_0
        statsmodels-0.4.3-np16py27_0
        statsmodels-0.4.3-np17py26_0
        statsmodels-0.4.3-np17py27_0
        wiserf-0.9-np17py27_0

conda ``depends`` with just ``--no-prefix -r`` shows us any version of numpy's dependencies in a more easily parsed
form, showing how many versions of numpy can be used to build that specific package.

.. code-block:: bash

    $ conda depends --no-prefix -r numpy
    The following packages depend on numpy:
        chaco-4.2.1.dev
        h5py-2.0.1 (2 builds)
        h5py-2.1.0 (2 builds)
        iopro-1.0 (2 builds)
        iopro-1.1.0 (2 builds)
        iopro-1.2rc1 (2 builds)

        ....

        pytables-2.4.0 (4 builds)
        scikit-learn-0.11 (13 builds)
        scikits-image-0.6.1 (6 builds)
        scipy-0.11.0 (3 builds)
        scipy-0.11.0rc2 (3 builds)
        statsmodels-0.4.3 (4 builds)
        wiserf-0.9

Adding the ``MAX_DEPTH`` command allows greater control over how many levels 
deep conda's dependency list will go.  By default, it is set to 0, but
for the purposes of demonstration, it is made explicit here.

.. code-block:: bash

    $ conda depends -rm 0 sqlite
    The following activated packages depend on sqlite:
        anaconda-launcher-0.0
        bitarray-0.8.0
        bitey-0.0
        conda-1.0
        cython-0.17.1
        dateutil-1.5
        flask-0.9
        gevent-0.13.7
        gevent-websocket-0.3.6
        
        ....

        sympy-0.7.1
        tornado-2.3
        werkzeug-0.8.3
        wiserf-0.9

In this example, setting the ``MAX_DEPTH`` to 1 shows only the packages 
that depend on sqlite, while not displaying what these packages depend
on, as well.

.. code-block:: bash

    $ conda depends -rm 1 sqlite
    The following activated packages depend on sqlite:
        python-2.7.3


.. _location_example:

Locations
---------

``conda locations`` displays the places conda will look for anaconda environments.  There is
a default environment at ``ROOT_DIR/envs``.

.. code-block:: bash

    $ conda locations
    System location for Anaconda environments:

        /Users/test/anaconda/envs

It is possible to add additional locations :ref:`by editing .condarc <config>`.  

Here is an example
of what will be displayed if additional locations have been created.

.. code-block:: bash

    $ conda locations
    System location for Anaconda environments:

    /Users/test/anaconda/envs

    User locations for Anaconda environments:

    /Users/test/envs

.. _envs_example:

Envs
----

``conda envs`` displays the ROOT_DIR anaconda directory, and test environments within it.

.. code-block:: bash

    $ conda envs
    Known Anaconda environments:

        /Users/test/anaconda
        /Users/test/anaconda/envs/test

----------------------------------
Managing Environments and Packages
----------------------------------

.. _create_example:

Create
------

In this example, we use ``conda create`` to make an environment in
a directory (specified with ``-p/--prefix``), for one or more packages.  We have also chosen to display
a progress bar, displayed as it creates the environment.


conda will also gather and activate all necessary package dependencies.  Those that are
not locally available will also be downloaded.

If the package version is not specified, conda will choose the latest version by
default.

It is also possible to disable a progress bar (``--progress-bar=no``) if you don't wish to show the status of any
packages conda has to download.

We'll start with a simple bare bones create.  

.. code-block:: bash

    conda create -n onlyScipy --progress-bar=no scipy

    The following packages will be activated:
        
        nose-1.1.2
        numpy-1.7.0b2
        python-2.7.3
        readline-6.2
        scipy-0.11.0
        sqlite-3.7.13
        zlib-1.2.7

    Proceed (y/n)? y


.. code-block:: bash

    $ conda create -p ~/anaconda/envs/test2 anaconda=1.1.4 python=2.7 numpy=1.6

        The following packages will be downloaded:
            
            anaconda-1.1.4-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            boto-2.6.0-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            h5py-2.1.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            imaging-1.1.7-py27_2.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            iopro-1.2rc1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            libpng-1.5.13-0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            llvmpy-0.8.4.dev-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            matplotlib-1.1.1-np16py27_1.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            mdp-3.3-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            numexpr-2.0.1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            pandas-0.9.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            pyflakes-0.5.0-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            pysal-1.4.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            pytables-2.4.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            pyzmq-2.2.0.1-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            scikit-learn-0.11-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            scikits-image-0.6.1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
            wakaridata-1.0-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]

        The following packages will be activated:
            
            anaconda-1.1.4
            anaconda-launcher-0.0
            ...
            numpy-1.6.2
            pandas-0.9.0
            pip-1.1
            pyflakes-0.5.0
            pygments-1.5
            pysal-1.4.0
            pysam-0.6
            pyside-1.1.2
            pytables-2.4.0
            python-2.7.3
            python.app-1.0
            ...
            yaml-0.1.4
            zeromq-2.2.0
            zlib-1.2.7

    Proceed (y/n)? y
    pyzmq-2.2.0.1-py27_0.tar.bz2 100% |######################################################################| Time: 0:00:00   1.26 MB/s
    pandas-0.9.0-np16py27_0.tar.bz2 100% |###################################################################| Time: 0:00:01   1.64 MB/s
    pysal-1.4.0-np16py27_0.tar.bz2 100% |####################################################################| Time: 0:00:00   1.28 MB/s
    mdp-3.3-np16py27_0.tar.bz2 100% |########################################################################| Time: 0:00:00   1.11 MB/s
    h5py-2.1.0-np16py27_0.tar.bz2 100% |#####################################################################| Time: 0:00:00   1.07 MB/s
    scikit-learn-0.11-np16py27_0.tar.bz2 100% |##############################################################| Time: 0:00:02 976.39 kB/s
    iopro-1.2rc1-np16py27_0.tar.bz2 100% |###################################################################| Time: 0:00:00 483.86 kB/s
    boto-2.6.0-py27_0.tar.bz2 100% |#########################################################################| Time: 0:00:00   1.84 MB/s
    llvmpy-0.8.4.dev-py27_0.tar.bz2 100% |###################################################################| Time: 0:00:00 239.90 kB/s
    pyflakes-0.5.0-py27_0.tar.bz2 100% |#####################################################################| Time: 0:00:00 162.98 kB/s
    numexpr-2.0.1-np16py27_0.tar.bz2 100% |##################################################################| Time: 0:00:00 212.51 kB/s
    libpng-1.5.13-0.tar.bz2 100% |###########################################################################| Time: 0:00:00   2.07 MB/s
    pytables-2.4.0-np16py27_0.tar.bz2 100% |#################################################################| Time: 0:00:01   1.16 MB/s
    wakaridata-1.0-py27_0.tar.bz2 100% |#####################################################################| Time: 0:00:00  85.65 kB/s
    imaging-1.1.7-py27_2.tar.bz2 100% |######################################################################| Time: 0:00:01 252.94 kB/s
    matplotlib-1.1.1-np16py27_1.tar.bz2 100% |###############################################################| Time: 0:00:23   1.14 MB/s
    anaconda-1.1.4-np16py27_pro0.tar.bz2 100% |##############################################################| Time: 0:00:00   5.13 MB/s
    scikits-image-0.6.1-np16py27_0.tar.bz2 100% |############################################################| Time: 0:00:04 592.53 kB/s

In this next example, rather than selecting an environment directory with a prefix, we will use the name option (``-n/--name``).
This will create an environment in the default Anaconda/envs ROOT_DIR (which can be displayed by using conda's :ref:`locations <location_example>` option), where it will be discoverable by using conda's
:ref:`envs <envs_example>` option.

.. code-block:: bash

    $ conda create -n test3 scipy 

    The following packages will be activated:
        
        nose-1.1.2
        numpy-1.7.0b2
        python-2.7.3
        readline-6.2
        scipy-0.11.0
        sqlite-3.7.13
        zlib-1.2.7

    Proceed (y/n)? y



.. _install_example:

Install
-------

``conda install`` places a package in an environment that may already exist,
in this case ``~/envs/test2``, the environment created in the previous example.

As before, conda will activate all necessary dependencies.

.. code-block:: bash

    $ conda install scipy -p ~/envs/test2 --progress-bar=yes

        The following packages will be downloaded:
            
            scipy-0.11.0-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]

        The following packages will be activated:
            
            scipy-0.11.0

    Proceed (y/n)? y
    scipy-0.11.0-np16py27_pro0.tar.bz2 100% |###############################| Time: 0:00:12 690.46 kB/s

.. _upgrade_example:

Upgrade
-------

Need an upgrade example.

.. _deactivate_example:

Deactivate
----------

.. code-block:: bash

  $ conda deactivate sphinx-1.1.3-py27_0

      The following packages will be DE-activated:
          
          sphinx-1.1.3

  Proceed (y/n)? y

.. _upgrade2pro_example:

upgrade2pro
-----------