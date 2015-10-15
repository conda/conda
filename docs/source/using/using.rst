Overview
========

.. contents::

The quickest way to start using conda is to use our :doc:`/install/quick` guide, then run through the 30-minute :doc:`Conda Test Drive </test-drive>`, which is a shortened version of this user guide.

Then refer to the more detailed instructions below for managing environments, Python and other packages.

For full usage of each command, check the  :doc:`/commands` guide. In your terminal window, you can 
enter the command name followed by --help. 

Introduction
~~~~~~~~~~~~~

You know that a package manager helps you find and install packages. But if you need a package that requires a different version of Python, there is no need to switch to a different environment manager, because conda is both a package manager and an environment manager. With just a few commands, you can set up a totally separate environment to run that different version of Python, and yet continue to run your usual version of Python in your normal environment. 

Anytime you wish to see the full documentation for any command, type the command followed by ``--help`` For example, to learn about the conda update command:   

.. code::

     conda update --help

The same help that is available in conda is also available online from our  :doc:`/commands`. 

Managing conda
~~~~~~~~~~~~~~~

NOTE: Whether you are using Linux, OS X or the Windows command prompt, in your terminal window the conda commands are all the same unless noted.

Verify that conda is installed, check current conda version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be sure that you are starting in the right place, let’s verify that you have successfully installed Anaconda. In your terminal window, enter the following:  

.. code::

   conda --version

Conda will respond with the version number that you have installed, like:  ``conda 3.11.0``

NOTE: If you see an error message, check to see that you are logged into the same user account that you used to install Anaconda or Miniconda, that you are in a directory that Anaconda or Miniconda can find,
and that you have closed and re-opened the terminal window after installing it. 

Update conda to the current version 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, let’s use the conda update command to update conda:
  
.. code::

   conda update conda

Conda will compare versions and let you know what is available to install. It will also tell you about other packages that will be automatically updated or changed with the update. If it tells you that a newer version of conda is available, type Y to update: 

.. code::

   Proceed ([y]/n)? y

:doc:`envs` is next.
