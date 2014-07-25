Overview of building conda's packages
=====================================

Continuum's conda toolset provides cross-platform binary package management.
Originally built to furnish Python distributions, the tools are in active
development and being applied in many use cases. This tutorial explores what
goes into building conda packages.

For a typical python-native binary package built in a Linux environment with

.. code-block:: bash
    $ python setup.py build; python setup.py install

conda packaging can be as simple as issuing a one-line command. Linked
libraries are located relative to the binary (rather than referenced with
absolute paths) and the software is bundled and ready to ship.

As we'll explore, other package builds are not trivial, especially if complex
dependencies are involved or the package was built in an ad-hoc way that does
not conform to the usual placement of files relative to one another. This
tutorial will move through the gradations of difficulty to illustrate both the
potential and challenges of applying conda to package and distribute your
software.

Presently, we're focused on bundling packages for Linux. Mac OS X and Windows
packages are supported, and future tutorials will cover the additional
considerations entailed therein.

Basic Concepts
--------------

The following assumes comfort navigating the UNIX command line and doing
routine shell script editing and file or directory manipulation. We'll touch on
some important concepts and resources you may want to read up on if you
encounter something unfamiliar.

Linking - Why are we doing this?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Why does conda exist? To address a problem that comes about because executables
depend on already-compiled libraries that are linked against at runtime. These
libraries may be system-level utilities, math packages, or ancillary
self-contained tools (like a visualization package). Many applications depend
on software like this, which can itself take up a lot of space and involve
other dependencies which make it complicated to install. Therefore, it's a
desirable model to build software that makes use of already-existing software,
rather than recompiling every time.

The challenge contained here is that your software must be able to locate
compatible builds to link against. If a link target can't be located or is an
outdated version, the software fails. conda provides a solution to manage
controlled, reproducible environments in which to run software with complex
dependencies.

Preliminaries
-------------

If any of the following are not installed in your Linux environment, you will want to install them:

.. code-block:: bash
    $ sudo apt-get install git
    $ sudo apt-get install chrpath

if Your Linux distribution is Debian/Ubuntu, or if you use CentOS/RedHat/Fedora distro:

.. code-block:: bash
    $ su

to become root, and then:

.. code-block:: bash
    $ yum install git
    $ yum install chrpath
    $ exit

If ''chrpath'' tool is not available for your Linux distribution you can skip it for now.
Later on you will have an another chance to do this, just after conda tool
installation (this will be installation of ''chrpath'' from official conda
repositories).

Besides, during below building processes you will be asked to upload packages to
`binstar.org <https://binstar.org>`_ hosting service. For now please just say no (or add
''--no-binstar-upload'' option to ''build'' conda's subcommand or ''conda-build''
command).

Install conda and conda-build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

conda is installed as part of `Continuum's Anaconda <https://store.continuum.io/cshop/anaconda/>`_
distribution and used to manage changes thereto. A lightweight `python + conda
standalone distribution <http://conda.pydata.org/miniconda.html`_ is also
available, which is what we'll assume here. Upon downloading the installer
script, make sure that this installer has appropriate permissions:

.. code-block:: bash
    $ chmod 755 Miniconda-3.5.2-Linux-x86_64.sh

and run it in a working directory:

.. code-block:: bash
    $ ./Miniconda-3.5.2-Linux-x86_64.sh

The list of all ''miniconda'' releases is available `here <http://repo.continuum.io/miniconda/>`_.

A fundamental design philosophy of conda is that users should have a fully
functioning programming environment in their home or working directory without
requiring administrative privileges or disrupting system- or root-level
software installations. Therefore you will not need administrative access to
run conda or manage conda environments. Building conda packages may, however,
require administrative privileges in certain cases.

Provide the script with your choices about where to install conda and whether
or not the path will be added to your environment. I will assume it is added to
the path; otherwise you will have to know the explicit path to your conda
executable.

Once conda is installed, relaunch a terminal window or issue:

.. code-block:: bash
    $ source ~/.bashrc

and confirm that:

.. code-block:: bash
    $ which conda

finds the executable where you have just installed it. If you did not prepend
the conda path (the default option), the ''which'' command will not find the
conda executable. You'll have to supply its path explicitly or create a soft
link, etc.

It's a useful habit to do:

.. code-block:: bash
    $ conda update conda

with a fresh install. You can issue to update command for any installed
package, including conda itself. This intrinsic bootstrapping capacity makes
conda very powerful. In fact, if you started with the miniconda installation,
you can expand it to the full [Anaconda
distribution](https://store.continuum.io/cshop/anaconda/) with:

.. code-block:: bash
    $ conda install anaconda

but that's not the focus here.

What you do need to install is ''conda-build'' tool:

.. code-block:: bash
    $ conda install conda-build

Besides, you can now easily install ''chrpath'' tool. Just type:

.. code-block:: bash
    $ conda install chrpath
    $ which chrpath

Relationship between conda build subcommand and conda-build command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At the beginning the ''build'' conda's subcommand was directly implemented in
itself code. During further development, implementation of this subcommand was
moved to separate tool - ''conda-build''. So, currently:

.. code-block:: bash
    $ conda build

means to run (as wrapper):

.. code-block:: bash
    $ conda-build

Clone conda-recipes from github
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is not a necessary step to build your own packages, but it's a very useful
resource to investigate already-built packages as a pretty good guide for your
task ahead.

.. code-block:: bash
    $ cd ~/
    $ git clone https://github.com/conda/conda-recipes

This will establish a copy of the conda-recipes repository on your local disk.
After getting familiar with full process of package building, feel free to add
your own new recipes to this repository by making a pull request.

Elementary conda Package Building
---------------------------------

Trivial
^^^^^^^

The simplest examples are very trivial. With a correct meta.yaml file and a
properly bundled binary distribution hosted on
`binstar.org <https://binstar.org>`_, this can be a one-liner:

.. code-block:: bash
    $ cd ~/conda-recipes/pyfaker
    $ conda build .

The result of above operation - the package - will be saved in ~/miniconda/conda-bld/linux-64/pyfaker-0.3.2-py27_0.tar.bz2 file.
You can easily install this in global miniconda environment:

.. code-block:: bash
    $ conda install ~/miniconda/conda-bld/linux-64/pyfaker-0.3.2-py27_0.tar.bz2
    $ python -c 'import faker; print "Successfully imported faker"'

Using conda skeleton to build from a PyPI package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, confirm that the package is hosted by `PyPI <https://pypi.python.org/>`_. Here I
use the ''music21'' package, motivated by a `recent
request <https://groups.google.com/a/continuum.io/forum/#!searchin/anaconda/conda$20package/anaconda/yu2ZKPI3ixU/VSWejiDoXlQJ>`_
on the `Anaconda support
list <https://groups.google.com/a/continuum.io/forum/#!forum/anaconda>`_. It
turns out this has already been packaged for conda, but it serves its purpose
as an example here:

.. code-block:: bash
    $ conda create -n tstenv pip
    $ conda info -e

The above command creates virtual environment with pip tool installed inside it.
Now I need to switch to just prepared environment by typing:

.. code-block:: bash
    $ source activate tstenv
    $ which pip

After that I can check ''music21'' package from `PyPI <https://pypi.python.org/>`_:

.. code-block:: bash
    $ pip install --allow-all-external music21

In this particular case where ''music21'' sources are placed on a remote
host (not on `PyPI <https://pypi.python.org/>`_ itself), the
''--allow-all-external'' option is mandatory.  Normally most packages sources are
directly available on `PyPI <https://pypi.python.org/>`_, so mentioned option
maybe omitted.

To verify if a package was properly installed, please just type:

.. code-block:: bash
    $ python -c 'import music21; print "Successfully imported music21"'

Don't bother about warning which says:

.. code-block:: bash
    Certain music21 functions might need these optional packages: matplotlib, numpy, ...

At this point it doesn't matter. We just wanted to check if ''music21'' can be
appropriately imported, and those packages are optional. If this goes well,
you can remove our virtual environment:

.. code-block:: bash
    $ source deactivate
    $ conda remove -n tstenv --all
    $ conda info -e

and generate a new conda recipe for ''music21'' package, by using `PyPI <https://pypi.python.org/>`_ metadata:

.. code-block:: bash
    $ cd ~/
    $ conda skeleton pypi music21 --no-download

The ''--no-download'' flag simply prevents the tarball from being downloaded again,
to save a couple minutes, since we just did that. You should verify the
existence of the ''meta.yaml'', ''build.sh'', and ''bld.bat'' files in a newly created
directory called ''music21''. Sometimes (like in this case - due to external place
of sources) it is necessary to cut value of md5 sum from ''fn:'' and ''url:''
directives in ''meta.yaml'' file, to ''md5:'' directive:

.. code-block:: yaml
    source:
      fn: music21-1.8.1.tar.gz#md5=b88f74b8a3940e4bca89d90158432ee0
      url: https://github.com/cuthbertLab/music21/releases/download/v1.8.1/music21-1.8.1.tar.gz#md5=b88f74b8a3940e4bca89d90158432ee0
      #md5:

to:

.. code-block:: yaml
    source:
      fn: music21-1.8.1.tar.gz
      url: https://github.com/cuthbertLab/music21/releases/download/v1.8.1/music21-1.8.1.tar.gz
      md5: b88f74b8a3940e4bca89d90158432ee0

Generally speaking, User should always check the ''meta.yaml'' file output from the
''skeleton'' subcommand invocation.

Now, it should be straightforward to use the ''conda-build'' tool. Let's try it:

.. code-block:: bash
    $ cd ~/music21/
    $ conda build .

Above command throws me an error:

.. code-block:: bash
    + /home/irritum/anaconda/envs/_build/bin/python setup.py install
    Traceback (most recent call last):
      File "setup.py", line 14, in <module>
        from setuptools import setup, find_packages
    ImportError: No module named setuptools
    Command failed: /bin/bash -x -e /home/irritum/music21/build.sh

So, now I should add appropriate requirement to auto generated ''meta.yaml'' file.
To do this, I need to change:

.. code-block:: yaml
    requirements:
      build:
        - python

to:

.. code-block:: yaml
    requirements:
      build:
        - python
        - setuptools

After above, I have re-run the command:

.. code-block:: bash
    $ conda build .

Now everything works great and the package was saved to ~/miniconda/conda-bld/linux-64/music21-1.8.1-py27_0.tar.bz2 file.
It's worth mentioning that during ''TEST'' phase of package it will be also placed in ~/miniconda/pkgs cache directory.
But this file shouldn't be used directly by anyone except the ''conda'' tool internally.

So, now I want to install ''music21'' package:

.. code-block:: bash
    $ conda install ~/miniconda/conda-bld/linux-64/music21-1.8.1-py27_0.tar.bz
    $ python -c 'import music21; print "Successfully imported music21"'

That's it :)

Writing meta.yaml by hand
^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose we stick with the same package, ''music21'', but don't start from the pip
installation. We can use common sense values for the ''meta.yaml'' fields, based on
other conda recipes and information about where to download the tarball. To
furnish a detailed failure mode, I'll take the ''meta.yaml'' file from the ''pyfaker''
package:

.. code-block:: yaml
    package:
      name: pyfaker

    source:
      git_tag: 0.3.2
      git_url: https://github.com/tpn/faker.git

    requirements:
      build:
        - python
        - setuptools

      run:
        - python

    test:
      imports:
        - faker

    about:
      home: http://www.joke2k.net/faker
      license: MIT

With a search on [github site of
music21](https://github.com/cuthbertLab/music21) and some sensible choices for
substitutions, I get a makeshift .yaml for ''music21'':

.. code-block:: yaml
    package:
      name: music21

    source:
      git_tag: 1.8.1
      git_url: https://github.com/cuthbertLab/music21/releases/download/v1.8.1/music21-1.8.1.tar.gz

    requirements:
      build:
        - python
        - setuptools

      run:
        - python

    test:
      imports:
        - music21

    about:
      home: https://github.com/cuthbertLab/music21
      license: LGPL

This seems reasonable. Being sure to supply ''build.sh'' and ''bld.bat'' files in the
same directory, I try:

.. code-block:: bash
    $ cd ~/music21/
    $ conda build .

and get a 403 error trying to access the repository. Now, with the benefit of
comparison with the skeleton-generated file, I observe that the key difference
is in the keywords that specify the git repository:

.. code-block:: yaml
    fn: music21-1.8.1.tar.gz
    url: https://github.com/cuthbertLab/music21/releases/download/v1.8.1/music21-1.8.1.tar.gz

versus:

.. code-block:: yaml
    git_tag: 1.8.1
    git_url: https://github.com/cuthbertLab/music21/releases/download/v1.8.1/music21-1.8.1.tar.gz

To answer of question what parameters should be used with what values, you will
find on page dedicated to [conda build
framework](http://conda.pydata.org/docs/build.html).

Uploading own packages to `binstar.org <https://binstar.org>`_
--------------------------------------------------------------

All of above steps produce one object - the package (tar archive compressed by
bzip2). During package building process we were asked if the package should be
uploaded to `binstar.org <https://binstar.org>`_. To get more info about
`binstar.org <https://binstar.org>`_ and possibility of uploading packages,
please visit it's `documentation page <http://docs.binstar.org/>`_.

Here is a minimal summary. First, we need a ''binstar'' client. We will install
this tool by running:

.. code-block:: bash
   $ conda install binstar

Now we should `register our account on binstar.org site <https://binstar.org/account/register>`_
and generate appropriate access TOKEN. If we already performed all
of this steps we are ready to upload our own package.
We have two ways to do this. The first option is to say ''yes'' during the build process.
This means you can re-run below commands one more time, but you have to agree with uploading:

.. code-block:: bash
    $ cd ~/music21/
    $ conda build .

The second way is to explicitly upload the already built package. You can do this by:

.. code-block:: bash
    $ binstar login
    $ binstar upload ~/miniconda/conda-bld/linux-64/music21-1.8.1-py27_0.tar.bz

Searching for already existing packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We have two methods to accomplish this task. First option is to use ''search''
conda's subcommand. You have to know that when this operation is requested then
''conda'' checks all available channels with packages (these channels are setup in
''.condarc'' file) in search of desired package.

Original ''.condarc'' file contains only default channels with software
officially maintained by `Continuum Analytics <http://continuum.io/>`_. This means we can
easily search for all packages from Anaconda's distribution. Therefore to
perform this search, please type (here I'm looking for the ''cmake'' package):

.. code-block:: bash
    $ conda search cmake

Sometimes we known that some person is constantly building new packages (and of
course publishing them on `binstar.org <https://binstar.org>`_) hosting service.
To be able to use those packages we have to add appropriate channel of that
person to our ''.condarc'' file, just like this:

.. code-block:: yaml
    channels:
        - defaults
        - http://conda.binstar.org/travis
        - http://conda.binstar.org/mutirri

In above example I have added two new channels (of user travis and user mutirri).
From now on I'm able to search for any requested package in these users package list (and of course I can install them also).

However, what I should do if I want to search through all channels without explicitly add them to my ''.condarc'' file?
Here is the answer:

.. code-block:: bash
    $ binstar search cmake

This command will search through all users packages on `binstar.org <http://binstar.org>`_.
**But remember**, to be able to install any of package which was found in this
way, you still have to add appropriate user's channel to ''.condarc'' file.
The another way to do this, is to run the conda tool with a special option (use
mutirri's channel and ''music21'' package in this case):

.. code-block:: bash
    $ conda install --channel http://conda.binstar.org/mutirri music21

or even shorter:

.. code-block:: bash
    $ conda install --channel mutirri music21

what means exactly the same thing.

More info about this topic can be found directly on `binstar.org documentation page <http://docs.binstar.org/>`_.

Issues/ Weird Stuff/ Needs Attention
------------------------------------

* conda-build splashes error asking for ''conda install jinja2'' to enable jinja
  template support. Build proceeds to completion without, but fails if it's
  installed with an error ''unable to load pkg_resources''.

* I have seen versions of this question on the support lists. If a user needs
  to maintain a conda environment with additional packages outside of conda
  control, what is the best practice? Is it worth considering a model where
  conda tracks not only packages under its control but also dependencies and
  version compatibility of packages that exist in the environment but are not
  conda-installed? In other words, a developer may not be able to offer a conda
  package for their software for technical reasons, but they may still want to
  support package info so that conda can be aware of that package and give the
  user instructions about updates and maintaining compatibility.

References
----------

`Using PyPI packages for conda <http://www.linkedin.com/today/post/article/20140107182855-25278008-using-pypi-packages-with-conda>`_
`music21 inquiry on support list <https://groups.google.com/a/continuum.io/forum/#!searchin/anaconda/conda$20package/anaconda/yu2ZKPI3ixU/VSWejiDoXlQJ>`_
