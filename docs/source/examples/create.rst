.. _create_example:

Create
------

In this example, we use ``conda create`` to make an environment in
a directory (specified with ``-p/--prefix``), for one or more packages.  We have also chosen to display
a progress bar, displayed as it creates the environment.


`conda` will also gather and activate all necessary package dependencies.  Those that are
not locally available will also be downloaded.

If the package version is not specified, `conda` will choose the latest version by
default.

We'll start with an environment created in a specific path (``~/anaconda/envs/test2``) using the --prefix option (``-p``).  

.. code-block:: bash

    $ conda create -p ~/anaconda/envs/test2 anaconda=1.1.4 python=2.7 numpy=1.6

    Package plan for creating environment at ~/anaconda/envs/test2:

    The following packages will be downloaded:

        anaconda-1.1.4-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        conda-1.0-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        gevent_zeromq-0.2.5-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        h5py-2.1.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        iopro-1.2rc1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        matplotlib-1.1.1-np16py27_1.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        mdp-3.3-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        numba-0.2-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        numbapro-0.6-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        numexpr-2.0.1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        numpy-1.6.2-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        pandas-0.9.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        pip-1.1-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        pysal-1.4.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        pytables-2.4.0-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        python-2.7.3-pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        scikit-learn-0.11-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        scikits-image-0.6.1-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        scipy-0.11.0-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]
        statsmodels-0.4.3-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]


    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        anaconda-1.1.4             |    np16py27_pro0
        anaconda-launcher-0.0      |           py27_0
        bitarray-0.8.0             |           py27_0
        bitey-0.0                  |           py27_0
        boto-2.6.0                 |           py27_0
        conda-1.0                  |           py27_0
        cython-0.17.1              |           py27_0
        dateutil-1.5               |           py27_0
        flask-0.9                  |           py27_0
        freetype-2.4.10            |                0
        gevent-0.13.7              |           py27_0
        gevent-websocket-0.3.6     |           py27_0
        gevent_zeromq-0.2.5        |           py27_0
        greenlet-0.4.0             |           py27_0
        grin-1.2.1                 |           py27_0
        h5py-2.1.0                 |       np16py27_0
        hdf5-1.8.9                 |                0
        imaging-1.1.7              |           py27_2
        iopro-1.2rc1               |       np16py27_0
        ipython-0.13               |           py27_0
        jinja2-2.6                 |           py27_0
        jpeg-8d                    |                0
        libevent-2.0.20            |                0
        libpng-1.5.13              |                0
        llvm-3.1                   |                0
        llvmpy-0.8.4.dev           |           py27_0
        matplotlib-1.1.1           |       np16py27_1
        mdp-3.3                    |       np16py27_0
        meta-0.4.2.dev             |           py27_0
        networkx-1.7               |           py27_0
        nose-1.1.2                 |           py27_0
        numba-0.2                  |       np16py27_0
        numbapro-0.6               |       np16py27_0
        numexpr-2.0.1              |       np16py27_0
        numpy-1.6.2                |           py27_0
        pandas-0.9.0               |       np16py27_0
        pip-1.1                    |           py27_0
        pyflakes-0.5.0             |           py27_0
        pygments-1.5               |           py27_0
        pysal-1.4.0                |       np16py27_0
        pysam-0.6                  |           py27_0
        pyside-1.1.2               |           py27_0
        pytables-2.4.0             |       np16py27_0
        python-2.7.3               |             pro0
        python.app-1.0             |           py27_0
        pytz-2012d                 |           py27_0
        pyyaml-3.10                |           py27_0
        pyzmq-2.2.0.1              |           py27_0
        qt-4.7.4                   |                0
        readline-6.2               |                0
        requests-0.13.9            |           py27_0
        scikit-learn-0.11          |       np16py27_0
        scikits-image-0.6.1        |       np16py27_0
        scipy-0.11.0               |    np16py27_pro0
        shiboken-1.1.2             |           py27_0
        spyder-2.1.11              |           py27_0
        sqlalchemy-0.7.8           |           py27_0
        sqlite-3.7.13              |                0
        statsmodels-0.4.3          |       np16py27_0
        sympy-0.7.1                |           py27_0
        tornado-2.3                |           py27_0
        wakaridata-1.0             |           py27_0
        werkzeug-0.8.3             |           py27_0
        yaml-0.1.4                 |                0
        zeromq-2.2.0               |                0
        zlib-1.2.7                 |                0


    Proceed (y/n)? 

    Fetching packages...

    conda-1.0-py27_0.tar.bz2 100% |##################################################################################| Time: 0:00:00  95.36 kB/s
    h5py-2.1.0-np16py27_0.tar.bz2 100% |#############################################################################| Time: 0:00:01 561.13 kB/s
    mdp-3.3-np16py27_0.tar.bz2 100% |################################################################################| Time: 0:00:00   1.25 MB/s
    matplotlib-1.1.1-np16py27_1.tar.bz2 100% |#######################################################################| Time: 0:00:19   1.36 MB/s
    iopro-1.2rc1-np16py27_0.tar.bz2 100% |###########################################################################| Time: 0:00:00   1.48 MB/s
    python-2.7.3-pro0.tar.bz2 100% |#################################################################################| Time: 0:00:10 896.98 kB/s
    numexpr-2.0.1-np16py27_0.tar.bz2 100% |##########################################################################| Time: 0:00:00 312.23 kB/s
    numba-0.2-np16py27_0.tar.bz2 100% |##############################################################################| Time: 0:00:00 694.58 kB/s
    pysal-1.4.0-np16py27_0.tar.bz2 100% |############################################################################| Time: 0:00:00   1.37 MB/s
    gevent_zeromq-0.2.5-py27_0.tar.bz2 100% |########################################################################| Time: 0:00:00 212.40 kB/s
    numpy-1.6.2-py27_0.tar.bz2 100% |################################################################################| Time: 0:00:01   2.08 MB/s
    numbapro-0.6-np16py27_0.tar.bz2 100% |###########################################################################| Time: 0:00:00 607.65 kB/s
    scipy-0.11.0-np16py27_pro0.tar.bz2 100% |########################################################################| Time: 0:00:04   1.75 MB/s
    scikit-learn-0.11-np16py27_0.tar.bz2 100% |######################################################################| Time: 0:00:01   1.41 MB/s
    pip-1.1-py27_0.tar.bz2 100% |####################################################################################| Time: 0:00:00 867.01 kB/s
    pandas-0.9.0-np16py27_0.tar.bz2 100% |###########################################################################| Time: 0:00:01   1.47 MB/s
    pytables-2.4.0-np16py27_0.tar.bz2 100% |#########################################################################| Time: 0:00:01 730.17 kB/s
    statsmodels-0.4.3-np16py27_0.tar.bz2 100% |######################################################################| Time: 0:00:04 964.62 kB/s
    anaconda-1.1.4-np16py27_pro0.tar.bz2 100% |######################################################################| Time: 0:00:00   4.48 MB/s
    scikits-image-0.6.1-np16py27_0.tar.bz2 100% |####################################################################| Time: 0:00:02   1.24 MB/s

    Activating packages...

    [      COMPLETE      ] |##############################################################################################################| 100%



In this next example, rather than selecting an environment directory with a prefix, we will use the name option (``-n/--name``).
This will create an environment in the default Anaconda/envs ROOT_DIR (which can be displayed by using `conda's` :ref:`info --locations <locations_example>` option), 
where it will be discoverable by using `conda's`
:ref:`info --envs <envs_example>` option.

It is also possible to disable a progress bar (``--quiet``) if you don't wish to show the status of any
packages `conda` has to download.

.. code-block:: bash

    $ conda create --quiet -n test3 scipy 

    Package plan for creating environment at ~/anaconda/envs/test3:

    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        nose-1.1.2                 |           py27_0
        numpy-1.7.0b2              |           py27_0
        python-2.7.3               |                4
        readline-6.2               |                0
        scipy-0.11.0               |       np17py27_1
        sqlite-3.7.13              |                0
        zlib-1.2.7                 |                0


    Proceed (y/n)? y

    Activating packages...

    [      COMPLETE      ] |##############################################################################################################| 100%




