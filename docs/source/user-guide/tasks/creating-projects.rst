=================
Creating projects
=================

In this tutorial, we will walk through how to set up a new Python project in conda
using an ``environment.yml`` file. This file will help you keep track of your
dependencies and share your project with others. We cover how to create your
project, add a simple Python program and update it with new dependencies.

Requirements
============

To follow along, you will need a working conda installation. Please head
over to our :doc:`installation guide <../install/index>` for instructions on how
to get conda install if you still do not have it.

This tutorial relies heavily on using your computer's terminal (Command Prompt or PowerShell
on Windows), so it is also important to have a working familiarity with using basic commands
such as ``cd`` and ``ls``.

Creating the project's files
============================

To start off, we will need a directory that will contain the files for our project. This can
be created with the following command::

    mkdir my-project

In this directory we will now create a new ``environment.yaml`` file which will hold the
dependencies for our Python project. In your text editor (e.g. VSCode, PyCharm, vim, etc.),
create this file and add the following:

.. code-block:: yaml

    name: my-project
    channels:
      - defaults
    dependencies:
      - python

Let's briefly go over what each part of this file means.

.. glossary::

    Name
        The name of your environment. Here we have chosen my-project, but this can be anything
        want

    Channels
        Channels specify where you want conda to search for packages. Here, we have chosen the ``defaults``
        channel, but others such as ``conda-forge`` or ``bioconda`` are also possible to list here.

    Dependencies
        All the dependencies that you need for your project. So far, we have just added ``python`` because
        we know it will be a Python project. We will add more later.


Creating our environment
========================

Now that we have a basic environment defined, we can create and activate this environment. To do so, run
the following commands::

    conda env create --file environment.yml
    conda activate my-project


Creating our Python application
===============================

Now that we have an environment with Python installed we can create a simple Python program.
In your project folder, create a ``main.py`` file and add the following:

.. code-block:: python

    def main():
        print("Hello conda!")


    if __name__ == "__main__":
        main()

We can run our simple Python program by running the following command::

    python main.py
    Hello conda!


Updating our project with new dependencies
==========================================

If you want you project to do more than the simple example above, you can use one of the thousands
of available packages on conda channels. To show how to do this, we will add several new dependencies
so that we can pull in some data from the internet and perform a basic analysis.

First, we need to fetch some data for our analysis. For this, we will use the
`Walkability Index <https://catalog.data.gov/dataset/walkability-index1>`_ available on `data.gov <https://data.gov>`_.
You can download this with the following command::

    curl -O https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv


*If you do not have curl, you can visit the above link with a web browser to download it.*
