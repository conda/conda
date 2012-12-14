.. _env_example:

Env
---

.. warning::
    conda env performs low level operations on Anaconda environments, and can potentially leave them in inconsistent or unusable states. It should not be needed for any common tasks.


``conda env --activate`` installs an Anaconda package with a specified :ref:`canonical names <canonical_name>` into an Anaconda environment at a given path, using the prefix option (``-p``).

.. code-block:: bash

    $ conda -ap ~/anaconda/envs/myenv numba-0.3.1-np17py27_0

    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        numba-0.3.1                |       np17py27_0


    Proceed (y/n)? y

    Activating packages...

    [      COMPLETE      ] |################################| 100%

By default, conda env (and many other `conda` commands) asks for permission before performing any operations.  This can be disabled with the optional argument ``--yes``.  For this next example, we will disable confirmation and
to activate a package inside a named environment using the --name prefix (``-n``).

.. code-block:: bash

    $ conda -an --yes myenv numba-0.3.1-np17py27_0

        The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        numba-0.3.1                |       np17py27_0


    Activating packages...

    [      COMPLETE      ] |################################| 100%


``conda env --deactivate`` removes one or more packages specified by :ref:`canonical names <canonical_name>` from an Anaconda environment at a given path, using the prefix option (``-p``).

.. code-block:: bash

    $ conda env -dp ~/anaconda/envs/myenv/ sqlite-3.7.13-0

    The following packages will be DE-activated:

        package                    |  build          
        -------------------------  |  ---------------
        sqlite-3.7.13              |                0


    The following packages will be left with BROKEN dependencies after this operation:

        package                    |  build          
        -------------------------  |  ---------------
        nose-1.1.2                 |           py27_0
        numpy-1.7.0b2              |           py27_0
        python-2.7.3               |                4
        scipy-0.11.0               |       np17py27_1


    Proceed (y/n)? y

    Deactivating packages...

    [      COMPLETE      ] |################################| 100%