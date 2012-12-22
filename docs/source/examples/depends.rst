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

To check a package dependency in a specific named environment in /anaconda/envs, the name option (``-n``) is used.

.. code-block:: bash

    $ conda depends -n foo numpy
        numpy depends on the following packages:
        nose-1.1.2
        python-2.7.3
        readline-6.2
        sqlite-3.7.13
        zlib-1.2.7

Running ``conda depends`` with the prefix option (``-p``) checks a specified packages dependencies within an Anaconda environment
located at a given path.

.. code-block:: bash

    $ conda depends -p ~/anaconda/envs/foo/ numpy
        numpy depends on the following packages:
        nose-1.1.2
        python-2.7.3
        readline-6.2
        sqlite-3.7.13
        zlib-1.2.7

    
Running ``conda depends`` with the reverse dependency command shows all packages that require NumPy.

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
more information and includes packages that depend on any version of NumPy.

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

``conda depends`` with just ``--no-prefix -r`` shows us any version of NumPy's dependencies in a more easily parsed
form, showing how many versions of NumPy can be used to build that specific package.

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


