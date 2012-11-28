.. _install_example:

Install
-------

``conda install`` places a package in an environment that may already exist,
in this case ``~/envs/test2``, the environment created in a previous example.

As before, conda will activate all necessary dependencies.

.. code-block:: bash

    $ conda install scipy -p ~/envs/test2 --progress-bar=yes

        The following packages will be downloaded:
            
            scipy-0.11.0-np16py27_pro0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]

        The following packages will be activated:
            
            scipy-0.11.0

    Proceed (y/n)? y
    scipy-0.11.0-np16py27_pro0.tar.bz2 100% |###############################| Time: 0:00:12 690.46 kB/s

