====
Info
====

I only use  ``Linux x86_64 (at the moment Debian) and Python 3.3 and later`` so the addons/changes are mostly reflecting that. 

``IMPORTANT:`` if you have a problem when using the conda_addons package ``do not`` ask for help at the official ContinuumIO-conda places:

- http://continuum.io/
- https://github.com/ContinuumIO/conda 
- https://github.com/pydata/conda


If you would like to see any features back-ported to the official ContinuumIO-conda you can only suggest such and such to them for consideration.

|

===========================
How to install conda_addons
===========================

You should have already installed an Anaconda/Miniconda Python 3 environment:
Probably the best way is to do it through the: `Miniconda3 (Python3) installers http://repo.continuum.io/miniconda/`

To use conda_addons there is an easy option to switch to it: check out the master: 

- https://github.com/peter1000/conda_addons.git
- or download a compressed package https://github.com/peter1000/conda_addons/archive/master.zip

Extact them somewhere: e.g. /home/conda_addons.

|

**In your conda config-file `.condarc`  set**

.. code-block:: 

    # directory in which conda root is located (used by `conda init`)
    root_dir: /home/conda_addons



than run from your normal anaconda/miniconda installation:

.. code-block:: bash

    $ conda init

outputs something like: 

``Initializing conda into: /home/workerm/Downloads/conda_addons``

And one should be ready to go.

|


**To revert back to the normal: conda** just ``comment out`` the 

.. code-block:: 

    # directory in which conda root is located (used by `conda init`)
    #root_dir: /home/conda_addons


and re-run:

.. code-block:: bash

    $ conda init



======
ADDONS 
======

are documented in the `README.rst file <README.rst>`_


|
|
|
|
|
|
|
|

==================================
Official ContinuumIO Documentation
==================================

See the `documentation <http://docs.continuum.io/conda/>`_ for more
information.

Conda has it's own mailing list created at: conda@continuum.io -
https://groups.google.com/a/continuum.io/forum/#!forum/conda
