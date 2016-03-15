=========
conda-env
=========

.. image:: https://travis-ci.org/conda/conda-env.svg
    :target: https://travis-ci.org/conda/conda-env

Provides the `conda env` interface to Conda environments.

Installing
----------

To install `conda env` with conda, run the following command in your root environment:

.. code-block:: bash

    $ conda install -c conda conda-env


Usage
-----
All of the usage is documented via the ``--help`` flag.

.. code-block:: bash

    $ conda env --help
    usage: conda-env [-h] {create,export,list,remove} ...

    positional arguments:
      {attach,create,export,list,remove,upload,update}
        attach              Embeds information describing your conda environment
                            into the notebook metadata
        create              Create an environment based on an environment file
        export              Export a given environment
        list                List the Conda environments
        remove              Remove an environment
        upload              Upload an environment to anaconda.org
        update              Updates the current environment based on environment
                            file

    optional arguments:
      -h, --help            show this help message and exit


``environment.yml``
-------------------
conda-env allows creating environments using the ``environment.yml``
specification file.  This allows you to specify a name, channels to use when
creating the environment, and the dependencies.  For example, to create an
environment named ``stats`` with numpy and pandas create an ``environment.yml``
file with this as the contents:

.. code-block:: yaml

    name: stats
    dependencies:
      - numpy
      - pandas

Then run this from the command line:

.. code-block:: bash

    $ conda env create
    Fetching package metadata: ...
    Solving package specifications: .Linking packages ...
    [      COMPLETE      ] |#################################################| 100%
    #
    # To activate this environment, use:
    # $ source activate numpy
    #
    # To deactivate this environment, use:
    # $ source deactivate
    #

Your output might vary a little bit depending on whether you have the packages
in your local package cache.

You can explicitly provide an environment spec file using ``-f`` or ``--file``
and the name of the file you would like to use.

Environment file example
-----------------------

.. code-block:: yaml

    name: stats
    channels:
      - javascript
    dependencies:
      - python=3.4   # or 2.7 if you are feeling nostalgic
      - bokeh=0.9.2
      - numpy=1.9.*
      - nodejs=0.10.*
      - flask
      - pip:
        - Flask-Testing

**Recommendation:** Always create your `environment.yml` file by hand.
