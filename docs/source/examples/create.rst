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



