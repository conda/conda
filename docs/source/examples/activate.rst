.. _activate_example:

Activate
--------


.. warning::
    conda activate performs low level operations on Anaconda installations and environments, and can potentially leave Anaconda environments in inconsistent or unusable states. It should not be needed for any common tasks.

``conda activate`` installs an Anaconda package with a specified :ref:`canonical names <canonical_name>` into an Anaconda environment at a given path, using the prefix option (``-p``).

.. code-block:: bash

    $ conda activate -p ~/anaconda/envs/myenv numba-0.3.1-np17py27_0

    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        numba-0.3.1                |       np17py27_0


    Proceed (y/n)? y

    Activating packages...

    [      COMPLETE      ] |##############################################################################################################| 100%