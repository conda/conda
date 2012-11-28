.. _locations_example:

Locations
---------

``conda locations`` displays the places conda will look for anaconda environments.  There is
a default environment at ``ROOT_DIR/envs``.

.. code-block:: bash

    $ conda locations
    System location for Anaconda environments:

        /Users/test/anaconda/envs

It is possible to add additional locations :ref:`by editing .condarc <config>`.  

Here is an example
of what will be displayed if additional locations have been created.

.. code-block:: bash

    $ conda locations
    System location for Anaconda environments:

    /Users/test/anaconda/envs

    User locations for Anaconda environments:

    /Users/test/envs

