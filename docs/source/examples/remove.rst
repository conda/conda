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