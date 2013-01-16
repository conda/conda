.. _info_example:

Info
----

``conda info`` provides information about anaconda environments.

.. code-block:: bash

    $ conda info

    Current Anaconda install:

                   target : pro
                 platform : osx-64
    conda command version : 1.1.0
           root directory : /Users/test/anaconda
       packages directory : /Users/test/anaconda/pkgs
          channel URLS : ['http://repo.continuum.io/pkgs/osx-64/']
    environment locations : ['/Users/test/anaconda/envs']

.. _envs_example:

``conda info --envs`` displays the ROOT_DIR anaconda directory, and test environments within it.

.. code-block:: bash

    $ conda info -e
    Known Anaconda environments:

        /Users/test/anaconda
        /Users/test/anaconda/envs/test

.. _locations_example:

``conda info --locations`` displays the places `conda` will look for anaconda environments.  There is
a default environment at ``ROOT_DIR/envs``.

.. code-block:: bash

    $ conda info -l

    Locations for Anaconda environments:

        /Users/test/anaconda/envs  (system location)

It is possible to add additional locations :ref:`by editing .condarc <config>`.  

Here is an example
of what will be displayed if additional locations have been created.

.. code-block:: bash

    $ conda info -l

    Locations for Anaconda environments:

        /Users/maggie/anaconda/envs  (system location) 
        /Users/test/envs