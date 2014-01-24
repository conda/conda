.. _create_example:

Create
------

In this example, we use ``conda create`` to make an environment in
a directory (specified with ``-p/--prefix``), for one or more packages.  We have also chosen to display
a progress bar, displayed as it creates the environment.


Conda will also gather and link all necessary package dependencies.
Those that are not locally available will also be downloaded.

If the package version is not specified, conda will choose the latest version by
default.

We'll start with an environment created in a specific path (`~/anaconda/envs/test2`) using the --prefix option (``-p``).

.. code-block:: bash

    $ conda create -p ~/anaconda/envs/test2 anaconda=1.4.0 python=2.7 numpy=1.6


    Package plan for creating environment at /Users/test/anaconda/envs/test2:

    The following packages will be downloaded:

        redis-py-2.7.2-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]
        scikit-image-0.8.2-np16py27_0.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]


    The following packages will be linked:

        package                    |  build
        -------------------------  |  ---------------
        _license-1.1               |           py27_0
        anaconda-1.4.0             |       np16py27_0
        astropy-0.2                |       np16py27_0
        biopython-1.60             |       np16py27_0

        ...

        xlwt-0.7.4                 |           py27_0
        yaml-0.1.4                 |                0
        zeromq-2.2.0               |                0
        zlib-1.2.7                 |                0


    Proceed (y/n)? y

    Fetching packages...

    redis-py-2.7.2-py27_0.tar.bz2 100% |##################################################################################| Time: 0:00:00 689.67 kB/s
    scikit-image-0.8.2-np16py27_0.tar.bz2 100% |##########################################################################| Time: 0:00:02   1.46 MB/s

    Linking packages...

    [      COMPLETE      ] |###################################################################################################################| 100%

    To activate this environment, type 'source activate test2'

    To deactivate this environment, type 'source deactivate'



In this next example, rather than selecting an environment directory with a prefix, we will use the name option (``-n/--name``).
This will create an environment in the default `Anaconda/envs` **ROOT_DIR** (which can be displayed by using conda's :ref:`info --locations <locations_example>` option),
where it will be discoverable by using conda's
:ref:`info --envs <envs_example>` option.

It is possible to disable a progress bar (``--quiet``) if you don't wish to show the status of any
packages conda has to download.  You can also skip the ``Proceed(y/n)?`` check with ``--yes``

.. code-block:: bash

    $ conda create --quiet --yes -n foo python

    Package plan for creating environment at /Users/test/anaconda/envs/foo:

    The following packages will be downloaded:

        sqlite-3.7.13-1.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]
        tk-8.5.13-1.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]
        zlib-1.2.7-1.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]


    The following packages will be linked:

        package                    |  build
        -------------------------  |  ---------------
        python-2.7.4               |                0
        readline-6.2               |                1
        sqlite-3.7.13              |                1
        tk-8.5.13                  |                1
        zlib-1.2.7                 |                1


    To activate this environment, type 'source activate foo'

    To deactivate this environment, type 'source deactivate'


To see what packages will be downloaded and/or used in an environment before creating it, you can use the ``--dry-run`` option.

.. code-block:: bash

    $ conda create --dry-run -n foo2 python

    Package plan for creating environment at /Users/maggie/anaconda/envs/foo2:

    The following packages will be linked:

        package                    |  build
        -------------------------  |  ---------------
        python-2.7.4               |                0
        readline-6.2               |                1
        sqlite-3.7.13              |                1
        tk-8.5.13                  |                1
        zlib-1.2.7                 |                1
