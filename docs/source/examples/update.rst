.. _update_example:

Update
-------

``conda update`` replaces old packages in a given environment with the latest versions.

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
