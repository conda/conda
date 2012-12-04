.. _remove_example:

Remove
------


.. warning::
    conda remove performs low level operations on Anaconda installations. It should not be needed for any common tasks.


``conda remove`` takes one or more :ref:`canonical names <canonical_name>` as arguments and removes them from local availability.

.. code-block:: bash

    $ conda remove zeromq-2.2.0-0
    The following packages were found and will be removed from local availability:

         zeromq-2.2.0-0

    Proceed (y/n)?