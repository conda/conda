Test drive
================

To start the conda 30-minute test drive, you should have already followed our 2-minute :doc:`/install/quick` guide to download, install and update Miniconda, OR have downloaded, installed and updated Anaconda or Miniconda on your own.

NOTE: After installing, be sure you have closed and then re-opened the terminal window so the changes can take effect.

Conda test drive milestones:
----------------------------

#. :ref:`USING CONDA<managing-conda>`. First we will verify that you have installed Anaconda or Miniconda, and check that it is updated to the current version. 3 min.
#. :ref:`MANAGING ENVIRONMENTS<managing-envs>`. Next we will play with environments by creating a few environments, so you can learn to move easily between the environments. We will also verify which environment you are in, and make an exact copy of an environment as a backup. 10 min.
#. :ref:`MANAGING PYTHON<managing-python>`. Then we will check to see which versions of Python are available to install, install another version of Python, and switch between versions. 4 min.
#. :ref:`MANAGING PACKAGES<managing-pkgs>`. We play with packages. We will a) list packages installed on your computer, b) see a list of available packages, and c) install and remove some packages using conda install. For packages not available using conda install, we will d) search on Anaconda.org. For packages that are in neither location, we’ll e) install a package with the pip package manager. We will also install a free 30 day trial of Continuum’s commercial package IOPro. 10 min.
#. :ref:`REMOVING PACKAGES, ENVIRONMENTS, OR CONDA<remove-pkgs-envs-conda>`. We’ll end the test drive by removing one or more of your test packages, environments, and/or conda,  if you wish. 3 min.

TOTAL 30 Minutes

TIP:  Anytime you wish to see the full documentation for any command, type the command followed by  ``--help``.
For example, to learn about the conda update command:

.. code::

   conda update --help

.. _managing-conda:

1. Managing conda
-----------------

Conda is both a package manager and an environment manager. You know that a package manager helps you find and
install packages. But let’s say that you want to use a package that requires a different version of Python than
you are currently using. With just a few commands you can set up a totally separate environment to run that
different version of Python, and yet continue to run your usual version of Python in your normal environment.
That’s the power of having an environment manager like conda.

TIP: Whether you are using Linux, OS X or the Windows command prompt, in your terminal window the conda commands
are all the same unless noted.

**Verify that conda is installed**

To be sure that you are starting in the right place, let’s verify that you have successfully installed Anaconda.
In your terminal window, enter the following:

.. code::

   conda --version

Conda will respond with the version number that you have installed, like:  ``conda 3.11.0``

NOTE: If you see an error message, check to see that you are logged into the same user account that you used
to install Anaconda or Miniconda, and that you have closed and re-opened the terminal window after installing it.

**Update conda to the current version**

Next, let’s use the conda update command to update conda:

.. code::

   conda update conda

Conda will compare versions and let you know what is available to install. It will also tell you about other
packages that will be automatically updated or changed with the update.

If a newer version of conda is available,
type Y to update:

.. code::

   Proceed ([y]/n)? y

When conda is updated, move to the next topic.

.. _managing-envs:

2. Managing environments
------------------------

Now let’s play with environments by creating a few, then moving between them.

**Create and activate an environment**

Use the conda create command, followed by any name you wish to call it:

.. code::

   conda create --name snowflakes biopython

This will create a new environment named /envs/snowflakes with the program Biopython.

TIP:  Many frequently used options after two dashes (``--``) can be abbreviated with just a dash and the
first letter. So ``--name`` and ``-n`` options are the same and ``--envs`` and ``-e`` are the same. See ``conda --help`` or
``conda -h`` for a list of abbreviations.

**Activate the new environment:**

* Linux, OS X: ``source activate snowflakes``
* Windows:  ``activate snowflakes``

TIP: Environments are installed by default into the envs directory in your conda directory. You can specify a
different path, see ``conda create --help`` for details.

TIP: Since we did not specify a version of Python, conda installs the same version that you used when you
download and installed conda.

**Create a second environment**

This time let’s create and name a new environment, AND install a different version of Python, and two packages
named Astroid and Babel:

.. code::

   conda create --name bunnies python=3 astroid babel

This will create a second new environment named /envs/bunnies with Python 3 and Astroid and Babel installed.

TIP: Install all the programs you will want in this environment at the same time. Installing one program at
a time can lead to dependency conflicts.

TIP: You can add much more to the conda create command, type ``conda create --help`` for details.

**List all environments**

Now let’s check to see which environments you have installed so far. Use the conda environment info command
to find out:

.. code::

   conda info --envs

You will see a list of environments like the following:

.. code::

   conda environments:

	snowflakes          * /home/username/miniconda/envs/snowflakes
	bunnies               /home/username/miniconda/envs/bunnies
        root                  /home/username/miniconda

**Verify current environment**

Which of these environments are you using right now -- snowflakes or bunnies? To find out, type the same command:

.. code::

   conda info --envs

Conda displays the list of all environments, with the current environment shown in (parentheses) or [brackets] in front of your prompt:

.. code::

   (snowflakes)

NOTE: conda also puts an asterisk (*) in front of the active environment in your environment list; see above in "List all environments."

**Switch to another environment (activate/deactivate)**

To change to another environment, type the following with the name of the environment:

* Linux, OS X: ``source activate bunnies``
* Windows:  ``activate bunnies``

To change your path from the current environment back to the root:

* Linux, OS X: ``source deactivate``
* Windows:  ``deactivate``

TIP: When the environment is deactivated, ``(bunnies)`` will no longer be shown in the prompt.

**Make an exact copy of an environment**

Make an exact copy of an environment by creating a clone of it. Here we will clone snowflakes to
create an exact copy named flowers:

.. code::

   conda create --name flowers --clone snowflakes

**Check to see the exact copy was made:**

.. code::

   conda info --envs

You should now see the three environments listed:  flowers, bunnies, and snowflakes.

**Delete an environment**

If you didn’t really want an environment named flowers, just remove it as follows:

.. code::

   conda remove --name flowers --all

To verify that the flowers environment has now been removed, type the command:

.. code::

   conda info --envs

Flowers is no longer in your environment list, so we know it was deleted.

**Learn more about environments**

To learn more about any conda command, just type the command followed by  ``--help``:

.. code::

   conda remove --help

.. _managing-python:

3. Managing Python
------------------

Conda treats Python the same as any other package, so it’s very easy to manage and update multiple installations.

**Check Python versions**

First let’s check to see which versions of Python are available to install:

.. code::

   conda search --full-name python

You can use ``conda search python`` to show all packages whose names contain the 
text "python" or add the ``--full-name`` option for only the packages whose full 
name is exactly "python".

**Install a different version of Python**

So now let’s say you need Python 3 to learn programming, but you don’t want to overwrite your Python 2.7
environment by updating Python. You can create and activate a new environment named snakes, and install
the latest version of Python 3 as follows:

.. code::

   conda create --name snakes python=3

* Linux, OS X: ``source activate snakes``
* Windows:  ``activate snakes``

TIP: It would be wise to name this environment a descriptive name like ``python3`` but that is not as much fun.

**Verify environment added**

To verify that the snakes environment has now been added, type the command:

.. code::

   conda info --envs

Conda displays the list of all environments, with the current environment shown in (parentheses) or [brackets] in front of your prompt:

.. code::

   (snakes)

**Verify Python version in new environment**

Verify that the snakes environment uses Python version 3:

.. code::

   python --version

**Use a different version of Python**

To switch to the new environment with a different version of Python, you simply need to activate it.
Let’s switch back to the default, 2.7:

* Linux, OS X: ``source activate snowflakes``
* Windows:  ``activate snowflakes``

**Verify Python version in environment**

Verify that the snowflakes environment uses the same Python version used when you installed conda:

.. code::

   python --version

**Deactivate this environment**

After you are finished working in the snowflakes environment, deactivate this environment and
revert your PATH to its previous state:

* Linux, OS X: ``source deactivate``
* Windows: ``deactivate``

.. _managing-pkgs:

4. Managing packages
--------------------

Now let’s play with packages. We’ve already installed several packages (Astroid, Babel and a specific
version of Python) when we created a new environment. We’ll check what packages we have, check what
are available, look for a specific package and install it. Then we’ll look for and install specific
packages on the Anaconda.org repository, install more using pip install instead of conda install, and
install a commercial package.

**View a list of packages and versions installed in an environment**

Use this to see which version of Python or another program is installed in the environment, or to confirm that a package has been added or removed.
In your terminal window, simply type:

.. code::

   conda list

**View a list of packages available with the conda install command**

A list of packages available for conda install, sorted by Python version, is available
from http://docs.continuum.io/anaconda/pkg-docs.html

**Search for a package**

First let’s check to see if a package we want is available for conda to install:

.. code::

   conda search beautifulsoup4

This displays the package, so we know it is available.

**Install a new package**

We will install Beautiful Soup into the current environment, using conda install as follows:

.. code::

   conda install --name bunnies beautifulsoup4

NOTE: You must tell conda the name of the environment (``--name bunnies``) OR it will install in
the current environment.

Now activate the bunnies environment, and do a conda list to see the new program installed:

* Linux, OS X: ``source activate bunnies``
* Windows:  ``activate bunnies``

All platforms:

.. code::

   conda list

**Install a package from Anaconda.org**

For packages that are not available using conda install, we can next look on Anaconda.org.
Anaconda.org is a package management service for both public and private package repositories.
Anaconda.org is a Continuum Analytics product, just like Anaconda and Miniconda.

TIP: You are not required to register with Anaconda.org to download files.

To download into the current environment from Anaconda.org, we will specify Anaconda.org as the
“channel” by typing the full URL to the package we want.

In a browser, go to http://anaconda.org.  We are looking for a package named “bottleneck” so in
the top left box named “Search Anaconda Cloud” type “bottleneck” and click the Search button.

There are more than a dozen copies of bottleneck available on Anaconda.org, but we want the most
frequently downloaded copy. So you can sort by number of downloads by clicking the “Downloads” heading.

Select the version that has the most downloads by clicking the package name.
This brings you to the Anaconda.org detail page that shows the exact command to use to download it:

.. code::

   conda install --channel https://conda.anaconda.org/pandas bottleneck


**Check to see that the package downloaded**

.. code::

   conda list

**Install a package with pip**

For packages that are not available from conda or Anaconda.org, we can often install the package with pip (short for "pip installs packages").

TIP:  Pip is only a package manager, so it cannot manage environments for you. Pip cannot even update
Python, because unlike conda it does not consider Python a package. But it does install some things
that conda does not, and vice versa. Both pip and conda are included in Anaconda and Miniconda.

We activate the environment where we want to put the program, then pip install a program named “See”:

* Linux, OS X: ``source activate bunnies``
* Windows:  ``activate bunnies``

All platforms:

.. code::

   pip install see

**Verify pip installs**

Check to see that See was installed:

.. code::

   conda list

**Install commercial package**

Installing commercial packages is the same as installing any other package with conda. So, as an example,
let’s install and then delete a free trial of one of Continuum’s commercial packages IOPro, which can speed
up your Python processing:

.. code::

   conda install iopro

TIP: Except for academic use, this free trial expires after 30 days.

You can now install and verify any package you want using conda, whether using the conda command, downloading from Anaconda.org, or using pip install, and whether open source or commercial.

.. _remove-pkgs-envs-conda:

5. Removing packages, environments, or conda
--------------------------------------------

Let’s end this test drive by removing one or more of your test packages, environments, and/or conda,  if you wish.

**Remove a package**

Let’s say that you decided not to continue using the commercial package IOPro.  You can remove it from the
bunnies environment with:

.. code::

   conda remove --name bunnies iopro

**Confirm that program has been removed**

Use conda list to confirm that IOPro has been removed:

.. code::

   conda list

**Remove an environment**

We no longer need the snakes environment, so type the command:

.. code::

   conda remove --name snakes --all

**Verify environment was removed**

To verify that the snakes environment has now been removed, type the command:

.. code::

   conda info --envs

Snakes is no longer shown in the environment list, so we know it was deleted.

**Remove conda**

* Linux, OS X:

Remove the Anaconda OR Miniconda install directory:

.. code::

   rm -rf ~/miniconda OR  rm -rf ~/anaconda

* Windows:  Go to Control Panel, click “Add or remove Program,” select “Python 2.7 (Anaconda)” OR “Python 2.7 Miniconda)” and click Remove Program.


**More resources**

* To read the full documentation for any conda command, type the command
  followed by  ``-h`` for “help.” For example, to learn about the conda update
  command: ``conda update -h``
* Full documentation: 	http://conda.pydata.org/docs/
* Cheat sheet: :doc:`/using/cheatsheet`
* FAQs: 				http://docs.continuum.io/anaconda/faq.html and :doc:`/faq`
* Free community support:	 https://groups.google.com/a/continuum.io/forum/#!forum/anaconda
* Paid support options:	http://continuum.io/support
* `Continuum Analytics Training & Consulting <http://continuum.io/contact-us>`_ : Continuum Analytics offers Python training courses. Our teaching philosophy is that the best way to learn is with hands-on experience to real world problems. Courses are available to individuals online, at numerous sites, or in-house at your place of business. We also offer consulting services for the analysis, management and visualization of scientific and business data or optimizing your processing workflows on modern hardware and GPUs.
