=====================
Managing environments
=====================

With conda, you can create, export, list, remove, and update environments that have different versions of Python and/or packages installed in them. Switching or moving between environments is called  activating the environment. You can even share an environment file with a coworker. 
 
Anytime you wish to see the full documentation for any command, type the command followed by  --help. For example, to learn about the conda environment command:   

.. code::

   conda env --help

The same help that is available in conda is also available online from our :doc:`command reference documentation </commands>`. 

Create an environment
----------------------

In order to manage environments, we need to create at least two so you can move or switch between them. 

To create a new environment, use the conda create command, followed by any name you wish to call it:

.. code::

   conda create --name snowflakes biopython

When conda asks you

.. code::

    proceed ([y]/n)? 

Type “y” for “yes.”

This will create a new environment named ``/envs/snowflakes`` that contains the program Biopython. This environment will use the same version of Python that you are currently using, because you did not specify a version. 

TIP:  Many frequently used options after two dashes (--) can be abbreviated with just a dash and the first letter. So --name and -n options are the same and --envs and -e are the same. See conda --help or conda -h for a list of abbreviations. 

Change environments (activate/deactivate)
----------------------------------------------------

**Linux, OS X:** ``source activate snowflakes``

**Windows:**  ``activate snowflakes``

Conda prepends the path name (snowflakes) onto your system command.

TIP: Environments are installed by default into the envs directory in your conda directory. You can specify a different path, see conda create --help for details. 

Deactivate the environment with the following:

**Linux, OS X:** ``source deactivate snowflakes``

**Windows:**  ``deactivate snowflakes``

Conda removes the path name (snowflakes) from your system command.

Create a separate environment
----------------------------------

So you can try switching or moving between environments, create and name a new environment. With this second environment, you can install a different version of Python, and a couple of packages:  

.. code::

   conda create --name bunnies python=3 astroid babel 

This will create a second new environment named /envs/bunnies with Python 3 and Astroid and Babel installed.

TIP: Install all the programs you will want in this environment at the same time. Installing one program at a time can lead to dependency conflicts.

TIP: You can add much more to the conda create command, type conda create --help for details.
List all environments

Now you can use conda to see which environments you have installed so far. Use the conda environment info command to find out: 

.. code::

   conda info --envs

You will see a list of environments like the following:

.. code::

   conda environments:
   snowflakes            /home/username/miniconda/envs/snowflakes
   bunnies               /home/username/miniconda/envs/bunnies

You can also use the conda environments list command as follows:

.. code::

   conda env list

The list of all environments will be the same with either command. 

Verify current environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Which environment are you using right now -- snowflakes or bunnies? To find out, type the command:  

.. code::

   conda info --envs

Conda displays the list of all environments, with the current environment shown in (parenthesis) in front of your prompt:  

.. code::

   (snowflakes) 

Clone an environment
-------------------------------------

Make an exact copy of an environment by creating a clone of it. Here we will clone snowflakes to create an exact copy named flowers:

.. code::

   conda create --name flowers --clone snowflakes

Check to see the exact copy was made: 

.. code::

   conda info --envs

You should now see the three environments listed:  flowers, bunnies, and snowflakes.

Remove an environment
-----------------------

If you didn’t really want an environment named flowers, just remove it as follows:

.. code::

   conda remove --name flowers --all

To verify that the flowers environment has now been removed, type the command:

.. code::

   conda info --envs

Flowers is no longer in your environment list, so we know it was deleted.

Share an environment 
------------------------

You may want to share your environment with another person, for example, so they can re-create a test that you have done. To allow them to quickly reproduce your environment, with all of its packages and versions, you can give them a copy of your environment.yml file. 

Export the environment file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable another person to create an exact copy of your environment, you will export the active environment file. 

Activate the environment you wish to export:

**Linux, OS X:** ``source activate peppermint``

**Windows:** ``activate peppermint``

NOTE: Replace “peppermint” with the name of the environment.

NOTE: If you already have an environment.yml file in your current directory, it will be overwritten with the new file. 

Export your active environment to the new file:

**All users:** ``conda env export > environment.yml``

Email or copy the exported environment.yml file to the other person.

Use environment from file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a copy of another developer’s environment from their environment.yml file:

Deactivate your current environment:

**Linux, OS X:** ``source deactivate starfish``

**Windows:** ``deactivate starfish``

NOTE: Replace “starfish” with the name of your current environment.

Make a new directory, change to the directory, and copy the environment.yml file into it. 

.. code::

   mkdir peppermint
   cd peppermint
   cp environment.yml

NOTE: Replace “peppermint” with the name of your directory.

In the same directory as the environment.yml file, create the new environment: 

.. code::

   conda env create

Activate the new environment:

**Linux, OS X:** ``source activate peppermint``

**Windows:** ``activate peppermint``

NOTE: Replace “peppermint” with the name of the environment.

Verify that the new environment was installed correctly:

.. code::

   conda list

Next, we'll take a look at managing Python.
