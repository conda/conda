=================================
Building a conda package for NLTK
=================================

The Natural Language Toolkit (NLTK) is a platform used for building Python 
programs that apply statistical natural language processing (NLP) to human 
language data. It can be difficult to install, but is easy when you build this 
NLTK conda package.

This package also includes all of the NLTK data sets, approximately 8 GB of
data.

Download the following files: https://gist.github.com/danielfrg/d17ffffe0dc8ed56712a0470169ff546
(click the Download  ZIP button on the top right).

Unzip the downloaded file and rename the downloaded directory to
``/nltk-with-data/``.

If not already installed, install conda build::

    conda install conda-build

Change directory to one directory above the nltk-with-data directory with
``cd``.

Run conda build for different Python versions that you need, selecting the
packages for the platform and OS you are running the command on:

.. code-block:: python

    conda build nltk-with-data --python 2.7
    conda build nltk-with-data --python 3.4
    conda build nltk-with-data --python 3.5
    conda build nltk-with-data --python 3.6

The resulting conda packages will be located in
$CONDA_ROOT/conda-bld/$ARCH/nltk-with-data.tar.bz2, where $CONDA_ROOT is the
root of your Anaconda installation and $ARCH is the architecture that you built
the packages on.

Upload the resulting conda packages to your local repository or to
`Anaconda Cloud <https://anaconda.org>`_ using the
`Anaconda Notebook Extension <https://docs.continuum.io/anaconda/jupyter-notebook-extensions>`_
anaconda-client CLI:

.. code-block:: bash

    anaconda upload $CONDA_ROOT/conda-bld/$ARCH/nltk-with-data.tar.bz2
    anaconda upload $CONDA_ROOT/conda-bld/$ARCH/nltk-with-data.tar.bz2
    anaconda upload $CONDA_ROOT/conda-bld/$ARCH/nltk-with-data.tar.bz2
    anaconda upload $CONDA_ROOT/conda-bld/$ARCH/nltk-with-data.tar.bz2

OPTIONAL: Build the conda package for other platforms (Win, Mac, Linux) by
repeating the above steps on those platforms. You may instead use conda convert
for pure Python packages. When newer versions of NLTK are released, you can
also update the recipe and repeat this process.

Install from conda
==================

.. code-block:: bash

    conda install nltk-with-data
    ipython

.. code-block:: python

    import nltk.corpus
    nltk.corpus.treebank

You'll see that the data is loaded using this conda package.

After you conda install the packages, use the library as usual with all of the
data sets.

SEE ALSO: `NLTK documentation <http://www.nltk.org/>`_
