.. _download_example:

Download
--------


.. warning::
    conda download performs low level operations on Anaconda installations and environments. It should not be needed for any common tasks.


``conda download`` takes as an argument a specified :ref:`canonical names <canonical_name>` and downloads it from available or known Anaconda repositories.

.. code-block:: bash

    $ conda download zeromq-2.2.0-0

    The following packages will be downloaded:

        zeromq-2.2.0-0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]


    Proceed (y/n)? y

    Fetching packages...

    zeromq-2.2.0-0.tar.bz2 100% |####################################################################################| Time: 0:00:01 222.27 kB/s