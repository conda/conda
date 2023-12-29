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
to get conda installed if you still do not have it.

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
        The name of your environment. Here, we have chosen the name "my-project", but this can
        be anything you want.

    Channels
        Channels specify where you want conda to search for packages. We have chosen the
        ``defaults`` channel, but others such as ``conda-forge`` or ``bioconda`` are also possible
        to list here.

    Dependencies
        All the dependencies that you need for your project. So far, we have just added ``python``
        because we know it will be a Python project. We will add more later.


Creating our environment
========================

Now that we have written a basic ``environment.yml`` file, we can create and activate an environment
from it. To do so, run the following commands::

    conda env create --file environment.yml
    conda activate my-project


Creating our Python application
===============================

With our new environment with Python installed, we can create a simple Python program.
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

If you want your project to do more than the simple example above, you can use one of the thousands
of available packages on conda channels. To demonstrate this, we will add a new dependency
so that we can pull in some data from the internet and perform a basic analysis.

To perform the data analysis, we will be relying on the `Pandas <https://pandas.pydata.org/docs/index.html>`_
package. To add this to our project, we will need to update our ``environment.yml`` file:

.. code-block:: yaml

    name: my-project
    channels:
      - defaults
    dependencies:
      - python
      - pandas  # <-- This is our new dependency

Once we have done that, we can run the ``conda env update`` command to install the new package::

    conda env update --file environment.yml


Now that our dependencies are installed, we will download some data to use for our analysis.
For this, we will use the U.S. Environmental Protection Agency's
`Walkability Index <https://catalog.data.gov/dataset/walkability-index1>`_ dataset
available on `data.gov <https://data.gov>`_. You can download this with the following command::

    curl -O https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv


.. admonition:: Tip

    If you do not have ``curl``, you can visit the above link with a web browser to download it.

For our analysis, we are interested in knowing what percentage of U.S. residents live in highly
walkable areas. This is a question that we can easily answer using the ``pandas`` library.
Below is an example of how you might go about doing that:

.. code-block:: python

    import pandas as pd


    def main():
        """
        Answers the question:

        What percentage of U.S. residents live highly walkable neighborhoods?

        "15.26" is the threshold on the index for a highly walkable area.
        """
        csv_file = "./EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv"
        highly_walkable = 15.26

        df = pd.read_csv(csv_file)

        total_population = df["TotPop"].sum()
        highly_walkable_pop = df[df["NatWalkInd"] >= highly_walkable]["TotPop"].sum()

        percentage = (highly_walkable_pop / total_population) * 100.0

        print(
            f"{percentage:.2f}% of U.S. residents live in highly" "walkable neighborhoods."
        )


    if __name__ == "__main__":
        main()

Update your ``main.py`` file with the code above and run it. You should get the following
answer::

    python main.py
    10.69% of Americans live in highly walkable neighborhoods


Conclusion
==========

You have just been introduced to creating your own data analysis project by using
the ``environment.yml`` file in conda. As the project grows, you may wish to add more dependencies
and also better organize the Python code into separate files and modules.

For even more information about working with environments and ``environment.yml`` files,
please see :doc:`Managing Environments <manage-environments>`.
