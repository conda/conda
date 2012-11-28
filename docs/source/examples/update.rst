.. _update_example:

Update
-------

``conda update`` replaces old packages in a given environment with the latest versions.

For this first example, we will use an environment ``/tmp/matplotlib11`` , which we can select using the prefix (``-p``) option.

.. code-block:: bash
  
  $ conda update -p /tmp/matplotlib11
  Upgrading Anaconda environment at /tmp/matplotlib11

    The following packages will be activated:
          
        matplotlib-1.2.0

    The following packages will be DE-activated:
          
        matplotlib-1.1.1

  Proceed (y/n)? y



For this next example, we will do almost the same thing, but instead of using the prefix option, we will use name (``-n``)
on an environment ``/home/test/anaconda/envs/matplotlib11``.

.. code-block:: bash
  
  $ conda update -n matplotlib11 
  Upgrading Anaconda environment at /home/test/anaconda

      The following packages will be activated:
          
          matplotlib-1.2.0

      The following packages will be DE-activated:
          
          matplotlib-1.1.1

  Proceed (y/n)? 


