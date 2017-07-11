===============================
Adding Windows Start menu items
===============================

When a package is installed, it can add a shortcut to the Windows 
**Start** menu. Conda and conda build handle this with the 
package `menuinst <https://github.com/ContinuumIO/menuinst>`_, 
which currently supports only Windows. For instructions on using 
``menuinst``, see 
`the menuinst wiki <https://github.com/ContinuumIO/menuinst/wiki>`_.

The easiest way to ensure that a package made with 
`conda constructor <https://github.com/conda/constructor>`_ does 
not install any menu shortcuts is to remove ``menuinst`` from 
the list of conda packages included. To do this, add the 
following to the ``constuct.yaml`` file:

.. code-block:: yaml

  exclude:
    - menuinst
