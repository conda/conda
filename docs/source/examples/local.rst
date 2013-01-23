.. _local_example:

Local
-----


.. warning::
    conda local performs low level operations on Anaconda installations. It should not be needed for any common tasks.


``conda local --download`` takes as an argument a specified :ref:`canonical names <canonical_name>` and downloads it from available or known Anaconda channels.

.. code-block:: bash

    $ conda local -d zeromq-2.2.0-0

    The following packages will be downloaded:

        zeromq-2.2.0-0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]


    Proceed (y/n)? y

    Fetching packages...

    zeromq-2.2.0-0.tar.bz2 100% |##############################################| Time: 0:00:01 222.27 kB/s


``conda local --remove`` takes one or more :ref:`canonical names <canonical_name>` as arguments and removes them from local availability.

.. code-block:: bash

    $ conda local -r zeromq-2.2.0-0
    The following packages were found and will be removed from local availability:

         zeromq-2.2.0-0

    Proceed (y/n)?