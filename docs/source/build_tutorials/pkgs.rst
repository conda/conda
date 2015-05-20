==========================================
Tutorial: Intro to building conda packages
==========================================
with conda skeleton
~~~~~~~~~~~~~~~~~~~~

This tutorial explores building a simple conda package using the conda skeleton command. Building a package 
makes it simple to install the program in any location. Many packages can be built using just the conda 
skeleton command with a few minor edits. Building conda packages can also be complex, especially if many 
dependencies are involved. 

TIP: A skeleton command generates a template that may be used as-is or with very few edits. See `skeleton (computer programming) <https://en.wikipedia.org/wiki/Skeleton_(computer_programming)/>`_.
 
This is the first of three tutorials on building conda packages.

Conda build summary
~~~~~~~~~~~~~~~~~~~

Building a simple conda package can be done in two steps, with two optional steps:

#. Before you start: make sure you have all the requirements.
#. Build a simple package with conda skeleton and PyPI: generate a simple package.
#. Optional - Convert conda package for other platforms: convert your simple package so it can be used on on Linux, Mac and Windows.
#. Optional - Upload package to Binstar.org: upload to a public or private repository so others can share your package.


1. Before you start
-------------------

You should already have conda and conda-build by downloading and installing Miniconda or Anaconda. 
Please follow the Quick Install instructions.

**Windows users only:*** install unxutils.

At the command prompt, enter the following: 

.. code-block:: bash

    conda install unxutils

**All users:** next, install conda-build: 

.. code-block:: bash

    conda install conda-build

Now you are ready to start building your own simple conda package.


2. Build a simple package with conda skeleton pypi
--------------------------------------------------

It is easy to build a skeleton recipe for any Python package that is hosted on PyPI, the official third-party 
software repository for the Python programming language. 

TIP: The conda skeleton command is also available for CPAN and CRAN repositories. Simply replace “pypi” with the repository name, either “cpan” or “cran.” 

Let’s generate a simple conda skeleton recipe for a package named Pyinstrument using existing PyPI metadata. 
Building a package will make it simple to install Pyinstrument in any location, especially if we choose to 
upload it to Binstar.org.

Pyinstrument is a Python statistical profiler that records the whole call stack once each millisecond, so 
programmers can see which parts of their code are slowest and how to make them faster. More information about
Pyinstrument: `https://github.com/joerick/pyinstrument <https://github.com/joerick/pyinstrument>`_

First, in your user home directory, run the conda skeleton command: 

.. code-block:: bash

    conda skeleton pypi pyinstrument

This creates a directory named pyinstrument and three skeleton files in that directory: meta.yaml, build.sh, 
and bld.bat. Use the ‘ls’ command on OS X or Linux or the “dir” command on Windows to verify that these files 
have been created.

Next, edit the new 50-line file meta.yaml.  This skeleton file can be fleshed out by filling in settings and 
commands, but for pyinstrument, any changes are optional.  

What are these three files?
    **meta.yaml:** Contains all the metadata in the recipe. Only package/name and package/version are required; everything else is optional.
    **build.sh:** Environment and other variables for Unix and Mac - whether 32 or 64-bit, path info, etc.
    **bld.bat:** The same environment and other variables for Windows.

Now that you have the skeleton ready, you can use the conda build tool. Let’s try it:

.. code-block:: bash

    conda build pyinstrument
    
When conda-build is finished, it displays the exact path and filename and location.

Linux example file path: 

.. code-block:: bash

    /home/jsmith/miniconda/conda-bld/linux-64/pyinstrument-0.13.1-py27_0.tar.bz2

Macintosh example file path: 

.. code-block:: bash

    /Users/jsmith/miniconda/conda-bld/osx-64/pyinstrument-0.13.1-py27_0.tar.bz2

Windows example file path: 

.. code-block:: bash

    C:\Users\jsmith\Miniconda\conda-bld\win-64\pyinstrument-0.13.1-py27_0.tar.bz2

NOTE: Your path and filename will vary depending on your installation and operating system. Save the 
path and filename information for the next step.

Now you can install your newly-built program on your local computer by using the use-local flag:

.. code-block:: bash

    conda install --use-local pyinstrument

Now verify that Pyinstrument installed successfully:

.. code-block:: bash

    conda list

3. Convert conda package for other platforms
-------------------------------------------------------

Now that you have built a package for your current platform with conda build, you can convert it for use on other platforms with the conda convert command and a platform specifier from the list {osx-64,linux-32,linux-64,win-32,win-64,all}. In the output directory, one folder will be created for each of the one or more platforms you chose, and each folder will contain a .tar.bz2 package file for that platform.

Linux and Macintosh users:

.. code-block:: bash

    conda convert --platform all /home/jsmith/miniconda/conda-bld/linux-64/pyinstrument-0.13.1-py27_0.tar.bz2 -o outputdir/

NOTE: Change your path and filename to the exact path and filename you saved in Step 2.

Windows users: 

.. code-block:: bash

    conda convert -f --platform all C:\Users\jsmith\Miniconda\conda-bld\win-64\pyinstrument-0.13.1-py27_0.tar.bz2 -o outputdir\

NOTE: Change your path and filename to the exact path and filename you saved in Step 2.

4. Optional - Upload packages to binstar.org
--------------------------------------------

Binstar is a repository for public or private packages. Uploading to Binstar allows you to easily install 
your package in any environment with just the conda install command, rather than manually copying or moving 
the tarball file from one location to another. You can choose to make your files public or private. For more 
info about binstar.org visit the Binstar documentation page.  

Open a free Binstar.org account and record your new binstar username and password.
Next, run conda install binstar and enter your binstar username and password. 
Next, log into your binstar.org account with the command:
binstar login

Now you can upload the new local packages to Binstar, as in this example:

binstar upload /home/jsmith/miniconda/conda-bld/linux-64/pyinstrument-0.12-py27_0.tar.bz

NOTE: Change your path and filename to the exact path and filename you saved in Step 2.

TIP: If you want to always automatically upload a successful build to Binstar, run:
conda config --set binstar_upload yes

You can log out of your binstar.org account with the command:

binstar logout

For more information about Binstar.org, see the binstar.org documentation page.

This completes the tutorial Intro to building conda packages using conda skeleton. 

Please see our next tutorial, Building conda packages part 2, to learn more about the files that 
go into each conda build and how to edit them manually. 



