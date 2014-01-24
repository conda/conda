.. _remove_example:

Remove
------

``conda remove`` is used to remove package(s) from a specified Anaconda environment.
**Note:** Because the package removed is the one specified, those packages which depend on it will not be removed.
To be sure that the action taken is the one desired, ``remove`` has a ``--dry-run`` option to show what would be done if
the command is executed.

.. code-block:: bash

    $ conda remove --dry-run -n foo numpy

    Package plan for package removal in environment /Users/test/anaconda/envs/foo:

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        numpy-1.7.1                |           py27_0

Actually running the command is much the same

.. code-block:: bash

    $ conda remove -n foo numpy

    Package plan for package removal in environment /Users/test/anaconda/envs/foo:

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        numpy-1.7.1                |           py27_0

    Proceed ([y]/n)? : y

    Unlinking packages ...
    [      COMPLETE      ] |###############| 100%

The ``--all`` option can be used to remove all packages from a given environment

.. code-block:: bash

    $ conda remove --all -n foo

    Package plan for package removal in environment /Users/test/anaconda/envs/foo:

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        python-2.7.5               |                1
        readline-6.2               |                1
        sqlite-3.7.13              |                1
        tk-8.5.13                  |                1
        zlib-1.2.7                 |                1

    Proceed ([y]/n)? : y

    Unlinking packages ...
    [      COMPLETE      ] |###############| 100%

The ``--features`` option can be used to remove a feature, such as MKL.
For example, if we have MKL installed, which we can see with ``conda
search``

.. code-block:: bash

    $ conda search scipy
    scipy                        0.11.0               np17py33_1
                                 0.11.0               np15py26_1
                                 0.11.0               np16py27_1
                                 0.11.0               np17py27_1
                                 0.11.0               np16py26_1
                                 0.11.0               np17py26_1
                                 0.11.0               np15py27_1
                                 0.12.0b1             np17py27_0
                                 0.12.0b1             np17py26_0
                                 0.12.0              np15py27_p0  [mkl]
                                 0.12.0               np15py27_0
                                 0.12.0               np16py26_0
                                 0.12.0              np15py26_p0  [mkl]
                                 0.12.0              np17py26_p0  [mkl]
                                 0.12.0              np16py27_p0  [mkl]
                                 0.12.0               np16py27_0
                                 0.12.0               np17py27_0
                              *  0.12.0              np17py27_p0  [mkl]
                                 0.12.0               np17py26_0
                                 0.12.0               np17py33_0
                                 0.12.0              np16py26_p0  [mkl]
                                 0.12.0               np15py26_0

We can see that SciPy 0.12.0 for NumPy 1.7 and Python 2.7 is installed with
the MKL feature.  To remove MKL, we would do

.. code-block:: bash

    $ conda remove --features mkl

    Package plan for package removal in environment /Users/test/Documents/Continuum/conda-recipes/vtk/testdir/test:

    The following packages will be downloaded:

        package                    |            build
        ---------------------------|-----------------
        numexpr-2.1                |       np17py27_0

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        mkl-11.0                   |      np17py27_p0
        mkl-rt-11.0                |               p0
        numexpr-2.1                |      np17py27_p0
        numpy-1.7.1                |          py27_p0
        scikit-learn-0.13.1        |      np17py27_p0
        scipy-0.12.0               |      np17py27_p0

    The following packages will be linked:

        package                    |            build
        ---------------------------|-----------------
        numexpr-2.1                |       np17py27_0
        numpy-1.7.1                |           py27_0
        scikit-learn-0.13.1        |       np17py27_0
        scipy-0.12.0               |       np17py27_0

    Proceed ([y]/n)?

And now we see that the same version of SciPy is installed, but without MKL
support.

.. code-block:: bash

    $conda search scipy
    scipy                        0.11.0               np17py33_1
                                 0.11.0               np15py26_1
                                 0.11.0               np16py27_1
                                 0.11.0               np17py27_1
                                 0.11.0               np16py26_1
                                 0.11.0               np17py26_1
                                 0.11.0               np15py27_1
                                 0.12.0b1             np17py27_0
                                 0.12.0b1             np17py26_0
                                 0.12.0              np15py27_p0  [mkl]
                                 0.12.0               np15py27_0
                                 0.12.0               np16py26_0
                                 0.12.0              np15py26_p0  [mkl]
                                 0.12.0              np17py26_p0  [mkl]
                                 0.12.0              np16py27_p0  [mkl]
                                 0.12.0               np16py27_0
                              *  0.12.0               np17py27_0
                                 0.12.0              np17py27_p0  [mkl]
                                 0.12.0               np17py26_0
                                 0.12.0               np17py33_0
                                 0.12.0              np16py26_p0  [mkl]
                                 0.12.0               np15py26_0

If we had just removed MKL without the ``--features`` option, it would
only remove MKL, but would not change the features of any of the installed
packages.

.. code-block:: bash

    $ conda remove mkl

    Package plan for package removal in environment /Users/test/Documents/Continuum/conda-recipes/vtk/testdir/test:

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        mkl-11.0                   |      np17py27_p0

    Proceed ([y]/n)?

    Unlinking packages ...
    [      COMPLETE      ] |###############| 100%
    $ conda search scipy
    scipy                        0.11.0               np17py33_1
                                 0.11.0               np15py26_1
                                 0.11.0               np16py27_1
                                 0.11.0               np17py27_1
                                 0.11.0               np16py26_1
                                 0.11.0               np17py26_1
                                 0.11.0               np15py27_1
                                 0.12.0b1             np17py27_0
                                 0.12.0b1             np17py26_0
                                 0.12.0              np15py27_p0  [mkl]
                                 0.12.0               np15py27_0
                                 0.12.0               np16py26_0
                                 0.12.0              np15py26_p0  [mkl]
                                 0.12.0              np17py26_p0  [mkl]
                                 0.12.0              np16py27_p0  [mkl]
                                 0.12.0               np16py27_0
                                 0.12.0               np17py27_0
                              *  0.12.0              np17py27_p0  [mkl]
                                 0.12.0               np17py26_0
                                 0.12.0               np17py33_0
                                 0.12.0              np16py26_p0  [mkl]
                                 0.12.0               np15py26_0
