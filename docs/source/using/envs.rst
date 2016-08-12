=====================
Managing environments
=====================

.. contents::

With conda, you can create, export, list, remove, and update environments that have different versions of Python and/or packages installed in them. Switching or moving between environments is called  activating the environment. You can even share an environment file with a coworker. 
 
Anytime you wish to see the full documentation for any command, type the command followed by  ``--help``. For example, to learn about the conda environment command:   

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

TIP:  Many frequently used options after two dashes (``--``) can be abbreviated with just a dash and the first letter. So ``--name`` and ``-n`` options are the same and ``--envs`` and ``-e`` are the same. See ``conda --help`` or ``conda -h`` for a list of abbreviations. 

Change environments (activate/deactivate)
----------------------------------------------------

**Linux, OS X:** ``source activate snowflakes``

**Windows:**  ``activate snowflakes``

Conda prepends the path name (snowflakes) onto your system command.

TIP: Environments are installed by default into the envs directory in your conda directory. You can specify a different path, see ``conda create --help`` for details. 

Deactivate the environment with the following:

**Linux, OS X:** ``source deactivate``

**Windows:**  ``deactivate``

Conda removes the path name (snowflakes) from your system command.

Create a separate environment
----------------------------------

So you can try switching or moving between environments, create and name a new environment. With this second environment, you can install a different version of Python, and a couple of packages:  

.. code::

   conda create --name bunnies python=3 astroid babel 

This will create a second new environment named /envs/bunnies with Python 3 and Astroid and Babel installed.

TIP: Install all the programs you will want in this environment at the same time. Installing one program at a time can lead to dependency conflicts.

TIP: You can add much more to the conda create command, type ``conda create --help`` for details.

List all environments
---------------------

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
--------------------------

Which environment are you using right now -- snowflakes or bunnies? To find out, type the command:  

.. code::

   conda info --envs

Conda displays the list of all environments, with the current environment 
highlighted with an '*' character.

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

NOTE: This file handles the environment's pip packages as well as its conda packages.

Email or copy the exported environment.yml file to the other person.

The other person will then need to create the environment by the following command:

``conda env create -f environment.yml``

Use environment from file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a copy of another developer’s environment from their environment.yml file:

.. code::

   conda env create -f environment.yml

Activate the new environment:

**Linux, OS X:** ``source activate peppermint``

**Windows:** ``activate peppermint``

NOTE: Replace “peppermint” with the name of the environment.

Verify that the new environment was installed correctly:

.. code::

   conda list

Build identical conda environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Explicit specification files can be used to build an identical conda environment on the same operating system platform, either on the same machine or a different machine.

The command ``conda list --explicit`` produces a spec list such as the following:

.. code::

    # This file may be used to create an environment using:
    # $ conda create --name <env> --file <this file>
    # platform: osx-64
    @EXPLICIT
    https://repo.continuum.io/pkgs/free/osx-64/mkl-11.3.3-0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/numpy-1.11.1-py35_0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/openssl-1.0.2h-1.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/pip-8.1.2-py35_0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/python-3.5.2-0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/readline-6.2-2.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/setuptools-25.1.6-py35_0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/sqlite-3.13.0-0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/tk-8.5.18-0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/wheel-0.29.0-py35_0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/xz-5.2.2-0.tar.bz2
    https://repo.continuum.io/pkgs/free/osx-64/zlib-1.2.8-3.tar.bz2

The command ``conda list --explicit > spec-file.txt`` creates a file containing this spec list in the current working directory. You may use the filename ``spec-file.txt`` or any other filename.

As the comment at the top of the file explains, the command ``conda create --name MyEnvironment --file spec-file.txt`` uses the spec file to create an identical environment on the same machine or another machine.

The command ``conda install --name MyEnvironment --file spec-file.txt`` adds these packages to an existing environment.

NOTE: These explicit spec files are not usually cross platform, and therefore have a comment at the top such as ``# platform: osx-64`` showing the platform where they were created. This platform is the one where this spec file is known to work. On other platforms, the packages specified might not be available or dependencies might be missing for some of the key packages already in the spec.

NOTE: Conda does not check architecture or dependencies when installing from an explicit specification file. To ensure the packages work correctly, be sure that the file was created from a working environment and that it is used on the same architecture, operating system and platform, such as ``linux-64`` or ``osx-64``.

Saved environment variables
---------------------------

Conda environments can include saved environment variables on Linux, macOS, and Windows.

Suppose you want an environment 'analytics' to store a secret key needed to log in to a server and a path to a configuration file. We will write a script named ``env_vars`` to do this.

Linux and macOS
~~~~~~~~~~~~~~~

Locate the directory for the conda environment, such as ``/home/jsmith/anaconda3/envs/analytics`` . Enter that directory and create these subdirectories and files::

  cd /home/jsmith/anaconda3/envs/analytics
  mkdir -p ./etc/conda/activate.d
  mkdir -p ./etc/conda/deactivate.d
  touch ./etc/conda/activate.d/env_vars.sh
  touch ./etc/conda/deactivate.d/env_vars.sh

Edit the two files. ``./etc/conda/activate.d/env_vars.sh`` should have this::

  #!/bin/sh

  export MY_KEY='secret-key-value'
  export MY_FILE=/path/to/my/file/

And ``./etc/conda/deactivate.d/env_vars.sh`` should have this::

  #!/bin/sh

  unset MY_KEY
  unset MY_FILE

Now when you use ``source activate analytics`` the environment variables MY_KEY and MY_FILE will be set to the values you wrote into the file, and when you use ``source deactivate`` those variables will be erased.

Windows
~~~~~~~

Locate the directory for the conda environment, such as ``C:\Users\jsmith\Anaconda3\envs\analytics`` . Enter that directory and create these subdirectories and files::

  cd C:\Users\jsmith\Anaconda3\envs\analytics
  mkdir .\etc\conda\activate.d
  mkdir .\etc\conda\deactivate.d
  type NUL > .\etc\conda\activate.d\env_vars.bat
  type NUL > .\etc\conda\deactivate.d\env_vars.bat

Edit the two files. ``.\etc\conda\activate.d\env_vars.bat`` should have this::

  set MY_KEY='secret-key-value'
  set MY_FILE=C:\path\to\my\file

And ``.\etc\conda\deactivate.d\env_vars.bat`` should have this::

  set MY_KEY=
  set MY_FILE=

Now when you use ``activate analytics`` the environment variables MY_KEY and MY_FILE will be set to the values you wrote into the file, and when you use ``deactivate`` those variables will be erased.

More notes on environment variable scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These script files can be part of a conda package, in which case these environment variables become active when an environment containing that package is activated.

Scripts can be given any name, but multiple packages may create script files, so be sure that you choose descriptive names for your scripts that are not used by other packages. One popular option is to give the script a name of the form packagename-scriptname.sh (or on Windows packagename-scriptname.bat).

Next, we'll take a look at :doc:`/py2or3`.
