.. _install_example:

Install
-------

``conda install`` places a package in an environment that may already exist,
in this case `/envs/myenv`.

As before, conda will link all necessary dependencies.

.. code-block:: bash

    $ conda install -p ~/anaconda/envs/myenv scipy

    Package plan for creating environment at /Users/maggie/anaconda/envs/myenv:

    The following packages will be downloaded:

        package                    |            build
        ---------------------------|-----------------
        flask-0.10.1               |           py27_1         129 KB
        itsdangerous-0.23          |           py27_0          16 KB
        jinja2-2.7.1               |           py27_0         307 KB
        markupsafe-0.18            |           py27_0          19 KB
        werkzeug-0.9.3             |           py27_0         385 KB

    The following packages will be linked:

        package                    |            build
        ---------------------------|-----------------
        flask-0.10.1               |           py27_1
        itsdangerous-0.23          |           py27_0
        jinja2-2.7.1               |           py27_0
        markupsafe-0.18            |           py27_0
        python-2.7.5               |                2
        readline-6.2               |                1
        sqlite-3.7.13              |                1
        tk-8.5.13                  |                1
        werkzeug-0.9.3             |           py27_0
        zlib-1.2.7                 |                1

    Proceed ([y]/n)? y

    Fetching packages ...
    flask-0.10.1-py27_1.tar.bz2 100% |#############################################################| Time: 0:00:00 331.31 kB/s
    itsdangerous-0.23-py27_0.tar.bz2 100% |########################################################| Time: 0:00:00 146.13 kB/s
    jinja2-2.7.1-py27_0.tar.bz2 100% |#############################################################| Time: 0:00:01 198.08 kB/s
    markupsafe-0.18-py27_0.tar.bz2 100% |##########################################################| Time: 0:00:00 187.88 kB/s
    werkzeug-0.9.3-py27_0.tar.bz2 100% |###########################################################| Time: 0:00:00 721.51 kB/s
    Extracting packages ...
    [      COMPLETE      ] |############################################################################################| 100%
    Linking packages ...
    [      COMPLETE      ] |############################################################################################| 100%
    #
    # To activate this environment, use:
    # $ source activate myenv
    #
    # To deactivate this environment, use:
    # $ source deactivate
    #



In this next example, using the name (``-n``) option will install a package or packages in an existing environment located in
`~/anaconda/envs`.

As with :ref:`conda create <create_example>`, we can use the ``--yes`` and ``--quiet`` options to automatically answer yes to the confirmation question and 
hide the progress bar, respectively.

.. code-block:: bash

    $ conda install --yes --quiet -n myenv pandas

    Package plan for installation in environment /Users/test/anaconda/envs/myenv:

    The following packages will be downloaded:

        package                    |            build
        ---------------------------|-----------------
        pandas-0.12.0              |       np17py27_0         3.4 MB

    The following packages will be linked:

        package                    |            build
        ---------------------------|-----------------
        dateutil-2.1               |           py27_1
        pandas-0.12.0              |       np17py27_0
        pytz-2013b                 |           py27_0
        six-1.3.0                  |           py27_0
