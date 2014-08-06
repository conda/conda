Overview of building conda packages
===================================

Continuum's conda toolset provides cross-platform binary package management.
Originally built to furnish Python distributions, the tools are in active
development and being applied in many use cases. This tutorial explores what
goes into building conda packages.

For a typical python-native binary package built in a Linux environment with

.. code-block:: bash

    $ python setup.py install

conda packaging can be as simple as issuing a one-line command. Linked
libraries are located relative to the binary (rather than referenced with
absolute paths) and the software is bundled and ready to ship.

As we'll explore, other package builds are not trivial, especially if complex
dependencies are involved or the package was built in an ad-hoc way that does
not conform to the usual placement of files relative to one another. This
tutorial will move through the gradations of difficulty to illustrate both the
potential and challenges of using conda to package and distribute your
software.

Install conda and conda-build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conda is installed as part of `Continuum's Anaconda
<https://store.continuum.io/cshop/anaconda/>`_ distribution. A lightweight
standalone distribution called `Miniconda
<http://conda.pydata.org/miniconda.html`_ is also available, which is what
we'll assume here. Upon downloading the installer script, make sure that this
installer has appropriate permissions:

On Linux and Mac OS X, run ``bash`` on the Miniconda installer, like

.. code-block:: bash

    $ bash Miniconda-3.5.2-Linux-x86_64.sh

(you may need to replace the filename with the correct filename for the
installer you downloaded)

On Windows, open and run the .exe installer.

You will not need administrative access to run Conda or manage Conda
environments.

Provide the script with your choices about where to install conda and whether
or not the path will be added to your environment. I will assume it is added to
the path; otherwise you will have to know the explicit path to your conda
executable.

Once Conda is installed, relaunch a terminal window and confirm that:

.. code-block:: bash

    $ conda info

finds the executable where you have just installed it. If you did add Anaconda
or Miniconda to your PATH (the default option) you will have to supply its
path explicitly.

It's a useful habit to do:

.. code-block:: bash

    $ conda update conda

with a fresh install. You can run the ``update`` command for any installed
package, including conda itself. This intrinsic bootstrapping capacity makes
conda very powerful. In fact, if you started with the Miniconda installation,
you can expand it to the full [Anaconda
distribution](https://store.continuum.io/cshop/anaconda/) with:

.. code-block:: bash

    $ conda install anaconda

but that's not the focus here.

What you do need to install is ``conda-build``:

.. code-block:: bash

    $ conda install conda-build

On Linux, you may also need to install ``patchelf``.

.. code-block:: bash

    $ conda install patchelf

Clone conda-recipes from GitHub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `conda recipes <https://github.com/conda/conda-recipes>`_ repo on GitHub
has many example conda recipes. This is not a necessary step to build your own
packages, but it's a very useful resource to investigate existing recipes for
similar packages to the one you are trying to build. In many cases, a recipe
for the package you are trying to build may already exist there. If you do not
have git installed you will need to install it first.

.. code-block:: bash

    $ git clone https://github.com/conda/conda-recipes

After getting familiar with full process of package building, feel free to add
your own new recipes to this repository by making a pull request.

Elementary conda Package Building
---------------------------------

Using conda skeleton to build from a PyPI package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is easy to build a skeleton recipe for any Python package that is hosted on
`PyPI
<https://pypi.python.org/>`_.


and generate a new conda recipe for ``music21`` package, by using `PyPI <https://pypi.python.org/>`_ metadata:

.. code-block:: bash

    $ cd ~/
    $ conda skeleton pypi music21

You should verify the
existence of the ``meta.yaml``, ``build.sh``, and ``bld.bat`` files in a newly created
directory called ``music21``. Sometimes (like in this case - due to external place
of sources) it is necessary to cut value of md5 sum from ``fn:`` and ``url:``
directives in ``meta.yaml`` file, to ``md5:`` directive:

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

Generally speaking, User should always check the ``meta.yaml`` file output from the
``skeleton`` subcommand invocation.

Now, it should be straightforward to use the ``conda-build`` tool. Let's try it:

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

So, now I should add appropriate requirement to auto generated ``meta.yaml`` file.
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
It's worth mentioning that during ``TEST`` phase of package it will be also placed in ~/miniconda/pkgs cache directory.
But this file shouldn't be used directly by anyone except the ``conda`` tool internally.

So, now I want to install ``music21`` package:

.. code-block:: bash

    $ conda install ~/miniconda/conda-bld/linux-64/music21-1.8.1-py27_0.tar.bz
    $ python -c 'import music21; print "Successfully imported music21"'

That's it :)

Writing meta.yaml by hand
^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose we stick with the same package, ``music21``, but don't start from the pip
installation. We can use common sense values for the ``meta.yaml`` fields, based on
other conda recipes and information about where to download the tarball. To
furnish a detailed failure mode, I'll take the ``meta.yaml`` file from the ``pyfaker``
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
substitutions, I get a makeshift .yaml for ``music21``:

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

This seems reasonable. Being sure to supply ``build.sh`` and ``bld.bat`` files in the
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

Here is a minimal summary. First, we need a ``binstar`` client. We will install
this tool by running:

.. code-block:: bash

   $ conda install binstar

Now we should `register our account on binstar.org site <https://binstar.org/account/register>`_
and generate appropriate access TOKEN. If we already performed all
of this steps we are ready to upload our own package.
We have two ways to do this. The first option is to say ``yes`` during the build process.
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

We have two methods to accomplish this task. First option is to use ``search``
conda's subcommand. You have to know that when this operation is requested then
``conda`` checks all available channels with packages (these channels are setup in
``.condarc`` file) in search of desired package.

Original ``.condarc`` file contains only default channels with software
officially maintained by `Continuum Analytics <http://continuum.io/>`_. This means we can
easily search for all packages from Anaconda's distribution. Therefore to
perform this search, please type (here I'm looking for the ``cmake`` package):

.. code-block:: bash

    $ conda search cmake

Sometimes we known that some person is constantly building new packages (and of
course publishing them on `binstar.org <https://binstar.org>`_) hosting service.
To be able to use those packages we have to add appropriate channel of that
person to our ``.condarc`` file, just like this:

.. code-block:: yaml

    channels:
        - defaults
        - http://conda.binstar.org/travis
        - http://conda.binstar.org/mutirri

In above example I have added two new channels (of user travis and user mutirri).
From now on I'm able to search for any requested package in these users package list (and of course I can install them also).

However, what I should do if I want to search through all channels without explicitly add them to my ``.condarc`` file?
Here is the answer:

.. code-block:: bash

    $ binstar search cmake

This command will search through all users packages on `binstar.org <http://binstar.org>`_.
**But remember**, to be able to install any of package which was found in this
way, you still have to add appropriate user's channel to ``.condarc`` file.
The another way to do this, is to run the conda tool with a special option (use
mutirri's channel and ``music21`` package in this case):

.. code-block:: bash

    $ conda install --channel http://conda.binstar.org/mutirri music21

or even shorter:

.. code-block:: bash

    $ conda install --channel mutirri music21

what means exactly the same thing.

More info about this topic can be found directly on `binstar.org documentation page <http://docs.binstar.org/>`_.

References
----------

`Using PyPI packages for conda <http://www.linkedin.com/today/post/article/20140107182855-25278008-using-pypi-packages-with-conda>`_
`music21 inquiry on support list <https://groups.google.com/a/continuum.io/forum/#!searchin/anaconda/conda$20package/anaconda/yu2ZKPI3ixU/VSWejiDoXlQJ>`_
