.. _depends_example:

Depends
-------

By default ``conda depends`` will simply display all dependencies
for a given package.

.. code-block:: bash

    $ conda depends scipy
    scipy depends on the following packages:
        nose-1.2.1
        numpy-1.7.0
        python-2.7.3
        readline-6.2
        sqlite-3.7.13
        tk-8.5.13
        zlib-1.2.7

To check a package dependency in a specific named environment in /anaconda/envs, the name option (``-n``) is used.

.. code-block:: bash

    $ conda depends -n foo scipy
    scipy depends on the following packages:
        nose-1.2.1
        numpy-1.7.0
        python-2.7.3
        readline-6.2
        sqlite-3.7.13
        tk-8.5.13
        zlib-1.2.7

Running ``conda depends`` with the prefix option (``-p``) checks a specified packages dependencies within an Anaconda environment
located at a given path.

.. code-block:: bash

    $ conda depends -p ~/anaconda/envs/foo/ scipy
    scipy depends on the following packages:
        nose-1.2.1
        numpy-1.7.0
        python-2.7.3
        readline-6.2
        sqlite-3.7.13
        tk-8.5.13
        zlib-1.2.7

    
Running ``conda depends`` with the reverse dependency command shows all packages that require NumPy.

.. code-block:: bash

    $ conda depends -r scipy
    The following activated packages depend on scipy:
        accelerate-1.0.1
        pandas-0.10.1
        pysal-1.5.0
        scikit-learn-0.13
        statsmodels-0.4.3
        wiserf-1.1

Using reverse dependency in addition to the verbose (``-v``) commands offers
more information and includes packages that depend on any version of NumPy.

.. code-block:: bash

    $ conda depends -rv scipy
    The following activated packages depend on scipy:
        accelerate-1.0.1-np17py27_p0
        pandas-0.10.1-np17py27_0
        pysal-1.5.0-np17py27_0
        scikit-learn-0.13-np17py27_0
        statsmodels-0.4.3-np17py27_0
        wiserf-1.1-np17py27_1


Adding the ``MAX_DEPTH`` command allows greater control over how many levels 
deep conda's dependency list will go.  By default, it is set to 0, but
for the purposes of demonstration, it is made explicit here.

.. code-block:: bash

$ conda depends -rm 0 sqlite
The following activated packages depend on sqlite:
    _license-1.1
    accelerate-1.0.1
    astropy-0.2
    biopython-1.60
    bitarray-0.8.1
    bitey-0.0
    boto-2.6.0
    chaco-4.2.1.dev
    cubes-0.10.2
    ...
    werkzeug-0.8.3
    wiserf-1.1
    xlrd-0.9.0
    xlwt-0.7.4

In this example, setting the ``MAX_DEPTH`` to 1 shows only the packages 
that depend on sqlite, while not displaying what these packages depend
on, as well.

.. code-block:: bash

    $ conda depends -rm 1 sqlite
    The following activated packages depend on sqlite:
        python-2.7.3


