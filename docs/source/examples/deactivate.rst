.. _deactivate_example:

Deactivate
----------


.. warning::
    conda deactivate performs low level operations on Anaconda installations and environments, and can potentially leave Anaconda environments in inconsistent or unusable states. It should not be needed for any common tasks.

``conda deactivate`` removes one or more packages specified by :ref:`canonical names <canonical_name>` from an Anaconda environment at a given path, using the prefix option (``-p``).

.. code-block:: bash

    $ conda deactivate -p ~/anaconda/envs/myenv/ sqlite-3.7.13-0

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

    [      COMPLETE      ] |##############################################################################################################| 100%

