===================================================
Building Anaconda Navigator app with conda skeleton
===================================================

Overview
--------

This tutorial will build an Anaconda Navigator app
for the `Rodeo IDE <https://www.yhat.com/products/rodeo>`_.


Who is this for?
----------------

This tutorial is for Windows, Mac, and Linux users who wish to generate an Anaconda Navigator app
conda package from a PyPi package. Prior knowledge of conda-build or conda recipes is recommended.


Conda build summary
~~~~~~~~~~~~~~~~~~~

Once the conda build recipe has been generated there are 3 modifications to the
recipe that need to be made. Finally, after the conda package has been uploaded
to your Anaconda Cloud channel it will be available on the Anaconda Navigator
Home pane.

#. :ref:`before-you-start4`
#. :ref:`skeleton`
#. :ref:`requires`
#. :ref:`app-entry`
#. :ref:`build-upload`
#. :ref:`navigator`
#. :ref:`troubleshooting1`
#. :ref:`help4`


.. _before-you-start4:

Before you start
----------------

You should already have installed Miniconda_ or Anaconda_.

.. _Miniconda: http://conda.pydata.org/docs/install/quick.html
.. _Anaconda: https://docs.continuum.io/anaconda/install

Install conda-build:

.. code-block:: bash

    conda install conda-build

It is recommended that you use the latest versions of conda and conda-build. To upgrade both packages run:

.. code-block:: bash

    conda upgrade conda
    conda upgrade conda-build

You will also need an account on `Anaconda Cloud <https://anaconda.org>`_.


.. _skeleton:

Create skeleton recipe
----------------------

First, in your user home directory, run the ``conda skeleton`` command:

.. code-block:: text

    conda skeleton pypi rodeo


This creates a directory named rodeo and creates three skeleton files in that directory: meta.yaml, build.sh,
and bld.bat. Use the ``ls`` command on OS X or Linux or the ``dir`` command on Windows to verify that these files
have been created.


.. _requires:

Requirements
------------

In a text editor change entries from ``ipython`` to ``jupyter`` in the ``requirements`` section.
The full ``requirements`` section will look like this.

.. code-block:: yaml

    requirements:
      build:
        - python
        - setuptools
        - jupyter
        - flask >=0.10.1
        - docopt
        - pyzmq >=13
        - mistune

  run:
        - python
        - jupyter
        - flask >=0.10.1
        - docopt
        - pyzmq >=13
        - mistune

.. _app-entry:

App entry in meta.yaml
----------------------

Next, you need to add a section called ``app`` that signal to Anaconda Navigator that this
pakcage contains an app entry.
The most important part of the ``app`` section is the ``entry`` tag, which defines how the
package is to be launched by Anaconda Navigator.
In many cases separate commands will need to be provided for Mac, Linux and Windows.

On Windows and Linux the ``entry`` tag is

.. code-block:: yaml

    app:
      entry: rodeo .                              [win]
      entry: rodeo .                              [linux]


For Mac OSX a launch script needs to be provided.
In a text editor create a new file in the conda build recipe directory called ``rodeo_mac.command``.
The contents of this file are

.. code-block:: bash

    DIR=$(dirname $0)

    $DIR/rodeo ${HOME}

To make sure that the file gets installed you also need to add these lines to the ``build.sh`` script.

.. code-block:: bash

    if [ `uname` == Darwin ]
    then
        cp $RECIPE_DIR/rodeo_mac.command $PREFIX/bin
    fi

Then in ``meta.yaml`` add this line to the ``app`` section.

.. code-block:: yaml

      entry: open ${PREFIX}/bin/rodeo_mac.command [osx]

Finally, a logo PNG file is provided in the conda build reciped that will be displayed
in Anaconda Navigator. You can download the
`app.png file <https://github.com/yhat/rodeo/blob/master/resources/app.png>` directly
from the Github repository.
This file must be downloaded to the same directory as the ``meta.yaml`` file.

The completed ``app`` section should look like this.

.. code-block:: yaml

    app:
      entry: rodeo .                              [win]
      entry: rodeo .                              [linux]
      entry: open ${PREFIX}/bin/rodeo_mac.command [osx]
      icon: app.png
      summary: Rodeo Data Science IDE
      type: web


You can download full versions of the `meta.yaml <./rodeo-meta.yaml>` and `build.sh <./rodeo-build.sh>` files.


.. _build-upload:

Build and upload
----------------


Now that you have the conda build recipe ready, you can use the conda-build tool to create the package.
You will have to build and upload the rodeo package separately on Mac, Linux and Windows machines in
order for the package to be available on all platforms.

.. code-block:: bash

    conda build rodeo

When conda-build is finished, it displays the exact path and filename of the conda package.
See the :ref:`troubleshooting` section if the conda-build command fails.

Windows example file path:

.. code-block:: text

    C:\Users\jsmith\Miniconda\conda-bld\win-64\rodeo-0.4.4-py35_0.tar.bz2

OS X example file path:

.. code-block:: text

    /Users/jsmith/miniconda/conda-bld/osx-64/rodeo-0.4.4-py35_0.tar.bz2

Linux example file path:

.. code-block:: text

    /home/jsmith/miniconda/conda-bld/linux-64/rodeo-0.4.4-py35_0.tar.bz2

NOTE: Your path and filename will vary depending on your installation and operating system. Save the
path and filename information for the next step.


Now you can upload the new local packages to Anaconda.org

Windows users:

.. code-block:: text

    anaconda upload C:\Users\jsmith\Miniconda\conda-bld\win-64\rodeo-0.4.4-py35_0.tar.bz2

Linux and OS X users:

.. code-block:: text

    anaconda upload /home/jsmith/miniconda/conda-bld/linux-64/rodeo-0.4.4-py35_0.tar.bz2


Note: Change your path and filename to the exact path and filename you saved in Step 2. Your path and filename
will vary depending on your installation and operating system.



For more information about Anaconda.org, see the `Anaconda.org documentation page <http://docs.anaconda.org/>`_.


.. _navigator:

Configure Anaconda Navigator
----------------------------

in Environments, click Channels
add https://conda.anaconda.org/CHANNEL

CHANNEL is your Anaconda cloud username

Restart Navigator



.. _`troubleshooting4`:

Troubleshooting
---------------


A. App does not appear on the home pane
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Check that the conda package has been uploaded to your Anaconda.org channel.

Check that your channel has been added to the Channels list.

You may have to remove your ``.anaconda/navigator`` directory and restart Navigator.



.. _`help4`:

Additional Information
----------------------
See the full conda skeleton documentation_ for more options.

.. _documentation: http://conda.pydata.org/docs/commands/build/conda-skeleton-pypi.html

For more information about adding Start Menu entries in Windows see the menuinst_ documentation.

.. _menuinst: https://github.com/ContinuumIO/menuinst/wiki
