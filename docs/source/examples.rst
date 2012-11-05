==================
Examples
==================


-------------------
Getting Information
-------------------

Info
----

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


List
----

.. code-block:: bash

    $ conda list -p ~/envs/test2
    nose                      1.1.2
    numpy                     1.6.2
    python                    2.7.3
    readline                  6.2
    sqlite                    3.7.13
    zlib                      1.2.7


Depends
-------

.. code-block:: bash

    $ conda depends numpy
    numpy depends on the following packages:
        nose 1.1.2
        python 2.7
        readline 6.2
        sqlite 3.7.13
        zlib 1.2.7

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

.. code-block:: bash

    $ conda depends -rvn numpy
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

.. code-block:: bash

    $ conda depends -rn numpy
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

.. code-block:: bash

    $ conda depends -rm 1 sqlite
    The following activated packages depend on sqlite:
        python-2.7.3



Search
------

.. code-block:: bash

    $ conda search numpy -p ~/anaconda/
    One match found compatible with environment /Users/test/anaconda/:

       package: numpy-1.7.0b2 
          arch: x86_64
      filename: numpy-1.7.0b2-py27_0.tar.bz2
           md5: bba52e6a2350d4f8f9279434137452f0


.. code-block:: bash

    $ conda search numpy -sp ~/envs/test2/
    One match found compatible with environment /Users/test/envs/test2/:

       package: numpy-1.6.2 
          arch: x86_64
      filename: numpy-1.6.2-py27_0.tar.bz2
           md5: 2dbc15e8687db0b0869cdecb59ff6454
      requires:
            nose-1.1.2
            python-2.7


Locations
---------

.. code-block:: bash

    $ conda locations
    System location for Anaconda environments:

        /Users/test/anaconda/envs


Envs
----

.. code-block:: bash

    $ conda envs
    Known Anaconda environments:

        /Users/test/anaconda
        /Users/test/anaconda/envs/test

----------------------------------
Managing Environments and Packages
----------------------------------


Create
------

.. code-block:: bash

    $ conda create ~/anaconda/envs/test2 --progress-bar=yes -p numpy=1.5

        The following packages will be downloaded:
            
            numpy-1.5.1-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]

        The following packages will be activated:
            
            nose-1.1.2
            numpy-1.5.1
            python-2.7.3
            readline-6.2
            sqlite-3.7.13
            zlib-1.2.7

    Proceed (y/n)? y
    numpy-1.5.1-py27_0.tar.bz2 100% |#####################################| Time: 0:00:06 321.12 kB/s


Install
-------

.. code-block:: bash

    $ conda install scipy -p ~/envs/test2 --progress-bar=yes

        The following packages will be downloaded:
            
            scipy-0.11.0-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]

        The following packages will be activated:
            
            scipy-0.11.0

    Proceed (y/n)? y
    scipy-0.11.0-np16py27_pro0.tar.bz2 100% |###############################| Time: 0:00:12 690.46 kB/s