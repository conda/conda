.. _update_example:

Update
-------

``conda update`` replaces old packages in a given environment with the latest
versions. Note that Python will not update past the major version that is
installed (so for example, if Python 2.7.4 is installed, ``conda update python`` will
install Python 2.7.7, not 3.4.1).

For this first example, we will use an environment */tmp/matplotlib*, which we can select using the prefix (``-p``) option.

.. code-block:: bash

    $ conda update -p /tmp/matplotlib matplotlib
    Upgrading Anaconda environment at /tmp/matplotlib

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        matplotlib-1.2.0           |       np17py27_1

    The following packages will be linked:

        package                    |            build
        ---------------------------|-----------------
        matplotlib-1.2.1           |       np17py27_1

    Proceed ([y]/n)?

For this next example, we will do almost the same thing, but instead of using the prefix option, we will use name (``-n``)
on an environment */home/test/anaconda/envs/matplotlib*.

.. code-block:: bash

    $ conda update -n matplot matplotlib
    Updating conda environment at /home/test/anaconda/envs/matplotlib

    The following packages will be UN-linked:

        package                    |            build
        ---------------------------|-----------------
        matplotlib-1.2.0           |       np17py27_1

    The following packages will be linked:

        package                    |            build
        ---------------------------|-----------------
        matplotlib-1.2.1           |       np17py27_1

    Proceed ([y]/n)? n

You can update all packages in an environment with ``conda update
--all``. Note that it is sometimes possible that this does not work, because
there is no satisfiable set of package dependencies without downgrades or
removals in the current environment.  In this case, conda will give an
``unsatisfiable package specifications`` error and will generate a hint
regarding which packages conflict with one another.
