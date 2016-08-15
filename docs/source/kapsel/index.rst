:orphan:

=====================
Conda kapsel tutorial
=====================

Conda kapsel automates setup steps such as installing the right
packages, downloading files, and configuring passwords so that
anyone who wants to look at your notebooks, Bokeh plots or other
analysis code can type ``conda kapsel run`` and have it Just
Work(tm).

Even if you never share your project with others, you will find it
more convenient to use ``conda kapsel`` than to manually maintain
an environment with commands such as ``conda install``.

In this tutorial, you will create a kapsel containing a Bokeh
application, then package it up as a zip file and "send" it to an
imaginary colleague. Your colleague will then be able to unpack it
and run it with a single command. You do not need to know Bokeh to
do this tutorial.

This tutorial is for all platforms: Windows, OS X and Linux.

NOTE: You must have `conda installed
<http://conda.pydata.org/docs/install/quick.html>`_ before
beginning this tutorial.

NOTE: Windows users using Python 3.5.1 should upgrade to Python 3.5.2+ 
with the command ``conda update python`` to avoid an issue with 
Windows and Python 3.5.1.

Install conda kapsel
====================

Create and activate a conda environment for this tutorial, naming
it "kapsel-tutorial".

**On Windows**::

  conda create -n kapsel-tutorial python
  activate kapsel-tutorial

**On OS X or Linux**::

  conda create -n kapsel-tutorial python
  source activate kapsel-tutorial

Next, use conda to install the keyring package from the
conda-forge channel::

  conda install -c conda-forge keyring

Next, use conda to install conda-kapsel from the conda-kapsel
channel::

  conda install -c conda-kapsel conda-kapsel

Test your installation by running the "version" command::

  conda kapsel --version

If it installed correctly, kapsel will respond with the version
number.

Create an empty project
=======================

We'll create a project directory called ``iris``. At the command
prompt, switch to a directory you'd like to contain the ``iris``
project. To create the ``iris`` project directory, type this::

    conda kapsel init --directory iris

It will ask you whether to create the ``iris`` directory. Type "y"
to confirm.  Your command line session will look something like
this::

    $ cd /home/alice/mystuff
    $ conda kapsel init --directory iris
    Create directory '/home/alice/mystuff/iris'? y
    Project configuration is in /home/alice/mystuff/iris/kapsel.yml

Optional: You can use your editor now to look through the file
``iris/kapsel.yml``. We won't edit ``kapsel.yml`` manually in this
tutorial, but you will see later that the commands we use in this
tutorial will modify it.

Before continuing, change into your new ``iris`` directory::

    cd iris

Get some data to work with
==========================

Often data sets are too large to keep locally, so you may want to
download them on demand. We'll use a small data set about iris
flowers to show how download on demand works.

Change into your new ``iris`` project directory, then copy and
paste in this code::

    conda kapsel add-download IRIS_CSV https://raw.githubusercontent.com/bokeh/bokeh/f9aa6a8caae8c7c12efd32be95ec7b0216f62203/bokeh/sampledata/iris.csv

After clicking "enter" ``conda kapsel`` downloads the data
file. You will see a new file ``iris.csv`` in your iris
directory. Now if you look at ``kapsel.yml``, you'll see a new
entry in the ``downloads:`` section.

Here's what the command line session looks like::

    $ cd /home/alice/mystuff/iris
    $ conda kapsel add-download IRIS_CSV  https://raw.githubusercontent.com/bokeh/bokeh/f9aa6a8caae8c7c12efd32be95ec7b0216f62203/bokeh/sampledata/iris.csv
    File downloaded to /home/alice/mystuff/iris/iris.csv
    Added https://raw.githubusercontent.com/bokeh/bokeh/f9aa6a8caae8c7c12efd32be95ec7b0216f62203/bokeh/sampledata/iris.csv to the project file.

TIP: The name ``IRIS_CSV`` shown on the second line is the name of
an environment variable. We'll get to those in a moment.

Create a command to run
=======================

A project should contain some sort of code, right? Let's make a
"hello world".  Create a file ``hello.py`` with these contents::

    print("hello")

Now you could run ``hello.py`` with the command ``python
hello.py``. But that won't do any ``conda kapsel`` magic. To be
sure things get set up, add ``hello.py`` as a project command,
like this::

    conda kapsel add-command hello "python hello.py"

It will ask you what kind of command it is; choose ``C`` for
command line. The command line session looks like::

    $ conda kapsel add-command hello "python hello.py"
    Is `hello` a (B)okeh app, (N)otebook, or (C)ommand line? C
    Added a command 'hello' to the project. Run it with `conda kapsel run hello`.

Now try ``conda kapsel run hello``. There will be a short delay as
the new dedicated project is created, and then it will print
"hello".

NOTE: Since you have only one command, plain ``conda kapsel run``
would work too.

When you run the command the second time, it runs much faster
because the dedicated project is already created.

In your ``iris`` directory, you will now see an ``envs``
subdirectory. By default every project has its own packages in its
own sandbox to ensure that projects do not interfere with one
another.

Now if you look at ``kapsel.yml`` in your text editor you will see
the ``hello`` command in the ``commands:`` section.

You can also list all the commands in your project by typing
``conda kapsel list-commands``::

    $ conda kapsel list-commands
    Commands for project: /home/alice/mystuff/iris

    Name      Description
    ====      ===========
    hello     python hello.py

Adding required packages
========================

In the next steps, we'll need to use some packages that aren't in
our ``iris/envs/default`` environment yet: Bokeh and Pandas.

In your ``iris`` directory, type::

    conda kapsel add-packages bokeh=0.12 pandas

The command line session will look something like::

    $ conda kapsel add-packages bokeh=0.12 pandas
    conda install: Using Anaconda Cloud api site https://api.anaconda.org
    Using Conda environment /home/alice/mystuff/iris/envs/default.
    Added packages to project file: bokeh=0.12, pandas.

If you look at ``kapsel.yml`` now, you'll see bokeh and pandas
listed under the ``packages:`` section. Since the packages have 
now been installed in your project's environment, you will also 
see files such as ``envs/YOUR-PATH-TO/bokeh``.

Configure your project with environment variables
=================================================

You may have wondered about that string ``IRIS_CSV`` when you
first looked in your ``kapsel.yml`` file. That's the environment
variable that tells your program where ``iris.csv`` lives. There
are also some other environment variables that ``conda kapsel``
sets automatically, such as ``PROJECT_DIR`` which locates your
project directory.

You can grab these variables from within your scripts with
Python's ``os.getenv`` function.

Let's make a script that prints out our data. In your text editor,
name the script ``showdata.py`` and paste in the following code::

    import os
    import pandas as pd

    project_dir = os.getenv("PROJECT_DIR")
    env = os.getenv("CONDA_DEFAULT_ENV")
    iris_csv = os.getenv("IRIS_CSV")

    flowers = pd.read_csv(iris_csv)

    print(flowers)
    print("My project directory is {} and my conda environment is {}".format(project_dir, env))

Save and close the editor. If you tried to run your new script now
with ``python showdata.py`` it probably wouldn't work, because
Pandas might not be installed yet and the environment variables
wouldn't be set.

Tell ``conda kapsel`` how to run your new script by adding a new
command called showdata::

    conda kapsel add-command showdata "python showdata.py"

(When prompted, choose "C" for "command line".)

Now run that new command at the command prompt::

    conda kapsel run showdata

You will see the data print out, and then the sentence about "My
project directory is... and my conda environment is...".

Good work so far!

Custom variables
================

Let's say your new command needs a database password, or has
another tunable parameter. You can require (or just allow) users
to configure these before the command runs.

NOTE: Encrypted variables such as passwords are treated
differently from plain variables. Encrypted variable values are
kept in the system keychain, while plain variable values are kept
in the file ``kapsel-local.yml``.

Let's try out a plain unencrypted variable first.

Type the command::

    conda kapsel add-variable COLUMN_TO_SHOW

In ``kapsel.yml`` you now have a variable named ``COLUMN_TO_SHOW``
in the ``variables:`` section, and ``conda kapsel list-variables``
lists ``COLUMN_TO_SHOW``.

Now modify your script ``showdata.py`` to use this new variable::

    import os
    import pandas as pd

    project_dir = os.getenv("PROJECT_DIR")
    env = os.getenv("CONDA_DEFAULT_ENV")
    iris_csv = os.getenv("IRIS_CSV")
    column_to_show = os.getenv("COLUMN_TO_SHOW")

    flowers = pd.read_csv(iris_csv)

    print("Showing column {}".format(column_to_show))
    print(flowers[column_to_show])
    print("My project directory is {} and my conda environment is {}".format(project_dir, env))

Because there's no value yet for ``COLUMN_TO_SHOW``, it will be
mandatory for users to provide one. Try this command::

   conda kapsel run showdata

The first time you run this, you will see a prompt asking you to
type in a column name. If you enter a column at the prompt (try
"sepal_length"), it will be saved in ``kapsel-local.yml``. Next
time you run it, you won't be prompted for a value.

To change the value in ``kapsel-local.yml``, use::

    conda kapsel set-variable COLUMN_TO_SHOW=petal_length

``kapsel-local.yml`` is local to this user and machine, while
``kapsel.yml`` is shared across all users of a project.

You can also set a default value for a variable in ``kapsel.yml``;
if you do this, users are not prompted for a value, but they can
override the default if they want to. Set a default value like
this::

   conda kapsel add-variable --default=sepal_width COLUMN_TO_SHOW

Now you should see the default in ``kapsel.yml``.

If you've set the variable in ``kapsel-local.yml``, the default
will be ignored.  You can unset your local override with::

   conda kapsel unset-variable COLUMN_TO_SHOW

The default will then be used when you ``conda kapsel run showdata``.

NOTE: ``unset-variable`` removes the variable value, but keeps the
requirement that ``COLUMN_TO_SHOW`` must be set.
``remove-variable`` removes the variable requirement from
``kapsel.yml`` so that the project will no longer require a
``COLUMN_TO_SHOW`` value in order to run.

An encrypted custom variable
============================

It's good practice to use variables for passwords and secrets in
particular.  This way, every user of the project can input their
own password, and it will be kept in their system keychain.

Any variable ending in ``_PASSWORD``, ``_SECRET``, or
``_SECRET_KEY`` is encrypted by default.

To create an encrypted custom variable, type::

    conda kapsel add-variable DB_PASSWORD

In ``kapsel.yml`` you now have a ``DB_PASSWORD`` in the
``variables:`` section, and ``conda kapsel list-variables`` lists
``DB_PASSWORD``.

From here, things work just like the ``COLUMN_TO_SHOW`` example
above, except that the value of ``DB_PASSWORD`` is saved in the
system keychain rather than in ``kapsel-local.yml``.

Try for example::

   conda kapsel run showdata

This will prompt you for a value the first time, and then save it
in the keychain and use it from there on the second run.  You can
also use ``conda kapsel set-variable DB_PASSWORD=whatever``,
``conda kapsel unset-variable DB_PASSWORD``, and so on.

Because this Iris example does not need a database password, we'll
now remove it. Type::

  conda kapsel remove-variable DB_PASSWORD

Creating a Bokeh app
====================

Let's plot that flower data!

Inside your ``iris`` project directory, create a new directory
``iris_plot``, and in it save a new file named ``main.py`` with
these contents::

    import os
    import pandas as pd
    from bokeh.plotting import Figure
    from bokeh.io import curdoc

    iris_csv = os.getenv("IRIS_CSV")

    flowers = pd.read_csv(iris_csv)

    colormap = {'setosa': 'red', 'versicolor': 'green', 'virginica': 'blue'}
    colors = [colormap[x] for x in flowers['species']]

    p = Figure(title = "Iris Morphology")
    p.xaxis.axis_label = 'Petal Length'
    p.yaxis.axis_label = 'Petal Width'

    p.circle(flowers["petal_length"], flowers["petal_width"],
             color=colors, fill_alpha=0.2, size=10)

    curdoc().title = "Iris Example"
    curdoc().add_root(p)

You should now have a file ``iris_plot/main.py`` inside the
project.  The ``iris_plot`` directory is a simple Bokeh app. (If
you aren't familiar with Bokeh you can learn more from the `Bokeh
documentation <http://bokeh.pydata.org/en/latest/>`_.)

To tell ``conda kapsel`` about the Bokeh app, be sure you are in
the directory "iris" and type::

    conda kapsel add-command plot iris_plot

When prompted, type ``B`` for Bokeh app. The command line session
looks like::

    $ conda kapsel add-command plot iris_plot
    Is `plot` a (B)okeh app, (N)otebook, or (C)ommand line? B
    Added a command 'plot' to the project. Run it with `conda kapsel run plot`.

NOTE: We use the app directory path, not the script path
``iris_plot/main.py``, to refer to a Bokeh app. Bokeh looks for
the file ``main.py`` by convention.

To see your Bokeh plot, run this command::

    conda kapsel run plot --show

``--show`` gets passed to the ``bokeh serve`` command, and tells
Bokeh to open a browser window. Other options for ``bokeh serve``
can be appended to the ``conda kapsel run`` command line as well,
if you like.

A browser window opens, displaying the Iris plot. Success!

Clean and reproduce
===================

You've left a trail of breadcrumbs in ``kapsel.yml`` describing
how to reproduce your project. Look around in your ``iris``
directory and you'll see you have ``envs/default`` and
``iris.csv``, which you didn't create manually. Let's get rid of
the unnecessary stuff.

Type::

    conda kapsel clean

``iris.csv`` and ``envs/default`` should now be gone.

Run one of your commands again, and they'll come back. Type::

    conda kapsel run showdata

You should have ``iris.csv`` and ``envs/default`` back as they
were before.

You could also redo the setup steps without running a
command. Clean again::

    conda kapsel clean

``iris.csv`` and ``envs/default`` should be gone again. Then re-prepare the project::

    conda kapsel prepare

You should have ``iris.csv`` and ``envs/default`` back again, but
this time without running a command.

Zip it up for a colleague
=========================

To share this project with a colleague, you likely want to put it
in a zip file.  You won't want to include ``envs/default``,
because conda environments are large and don't work if moved
between machines. If ``iris.csv`` were a larger file, you might
not want to include that either. The ``conda kapsel archive``
command automatically omits the files it can reproduce
automatically.

Type::

   conda kapsel archive iris.zip

You will now have a file ``iris.zip``. If you list the files in
the zip, you'll see that the automatically-generated ones aren't
in there::

    $ unzip -l iris.zip
    Archive:  iris.zip
      Length      Date    Time    Name
    ---------  ---------- -----   ----
           16  06-10-2016 10:04   iris/hello.py
          281  06-10-2016 10:22   iris/showdata.py
          222  06-10-2016 09:46   iris/.kapselignore
         4927  06-10-2016 10:31   iris/kapsel.yml
          557  06-10-2016 10:33   iris/iris_plot/main.py
    ---------                     -------
         6003                     5 files

NOTE: There's a ``.kapselignore`` file you can use to manually
exclude anything you don't want in your archives.

NOTE: ``conda kapsel`` also supports creating ``.tar.gz`` and
``.tar.bz2`` archives. The archive format will match the filename
you provide.

When your colleague unzips the archive, they can list the commands
in it::

    $ conda kapsel list-commands
    Commands for project: /home/bob/projects/iris

    Name      Description
    ====      ===========
    hello     python hello.py
    plot      Bokeh app iris_plot
    showdata  python showdata.py


Then your colleague can type ``conda kapsel run showdata`` (for
example), and ``conda kapsel`` will download the data, install
needed packages, and run the command.

Next steps
==========

There's much more that ``conda kapsel`` can do.

 * It can automatically start processes that your commands depend
   on. Right now it only supports starting Redis, for
   demonstration purposes. Use the ``conda kapsel add-service
   redis`` command to play with this. More kinds of service will
   be supported soon! Let us know if there are particular ones
   you'd find useful.
 * You can have multiple conda environment specifications in your
   project, which is useful if some of your commands use a
   different version of Python or otherwise have distinct
   dependencies. ``conda kapsel add-env-spec`` adds these
   additional environment specs.
 * Commands can be ipython notebooks. If you create a notebook in
   your project directory it will automatically be listed in
   ``conda kapsel list-commands``.
