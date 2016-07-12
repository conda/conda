:orphan:

==========================
Conda kapsel configuration
==========================

The ``conda kapsel`` command works with *project directories*,
which can contain scripts, notebooks, data files... anything
that is related to your project.

Any directory can become a kapsel; tell conda about your project
with a configuration file named ``kapsel.yml``.

``.yml`` files are in the YAML format and follow the YAML syntax.

TIP: Read more about YAML syntax at http://yaml.org/start.html

``kapsel.yml`` and ``kapsel-local.yml``
=========================================

Conda kapsels are affected by two configuration files,
``kapsel.yml`` and ``kapsel-local.yml``.

The file ``kapsel.yml`` contains information about a project that
is intended to be shared across users and machines. If you use
source control, the file ``kapsel.yml`` should probably be put in
source control.

The file ``kapsel-local.yml``, on the other hand, goes in
``.gitignore`` (or ``.svnignore`` or equivalent), because it
contains your local configuration state that you do not
want to share with others.

Both files can be manipulated with ``conda`` commands, so there's
rarely a need to hand-edit them, but you can if you like.

Commands and Requirements
=========================

In the ``kapsel.yml`` file you can define *commands* and
*requirements* that the commands need in order to run them.

For example, let's say you have a script named ``analyze.py``
in your project directory along with a file ``kapsel.yml``:

.. code-block:: yaml

  myproject/
     analyze.py
     kapsel.yml

The file ``kapsel.yml`` tells conda how to run your project:

.. code-block:: yaml

  commands:
    default:
      unix: "python ${PROJECT_DIR}/analyze.py"
      windows: "python %PROJECT_DIR%\analyze.py"

There are separate command lines for Unix shell (Linux and
Mac) and for Windows. If you only care about one platform, you
are not required to provide command lines for other platforms.

When you send your project to someone else, they can type
``conda kapsel run`` to run your script. The cool part
is that ``conda kapsel run`` makes sure that all
prerequisites are set up *before* it runs the script.

Let's say your script requires a certain conda package to be
installed. Add the ``redis-py`` package to ``kapsel.yml`` as a
dependency:

.. code-block:: yaml

  packages:
    - redis-py

Now when someone runs ``conda kapsel run`` the script is
automatically run in a conda environment that has ``redis-py``
installed.

Here's another example. Let's say your script requires a huge
data file that you don't want to put in source control and
you don't want to email. You can add a requirement to be
downloaded locally:

.. code-block:: yaml

  downloads:
    MYDATAFILE:
      url: http://example.com/bigdatafile
      sha1: da39a3ee5e6b4b0d3255bfef95601890afd80709

Now when someone runs ``conda kapsel run``, the file is
downloaded if it hasn't been downloaded already, and the
environment variable ``MYDATAFILE`` is set to the local
filename of the data. In your ``analyze.py`` file you can write
something like this:

.. code-block:: python

   import os
   filename = os.getenv('MYDATAFILE')
   if filename is None:
     raise Exception("Please use 'conda kapsel run' to start this script")
   with open(filename, 'r') as input:
     data = input.read()
     # and so on

``conda kapsel`` supports many other requirements,
too. Instead of writing long documentation about how to set up
your script before others can run it, simply put the requirements in
a ``kapsel.yml`` file and let ``conda kapsel`` check the setup
automatically.

Multiple Commands
=================

A ``kapsel.yml`` can list multiple commands. Each command has a
name; ``conda kapsel run COMMAND_NAME`` runs the command named
``COMMAND_NAME``.

``conda kapsel list-commands`` lists commands, along with a
description of each command. To customize a command's description,
add a ``description:`` field in ``kapsel.yml``, like this:

.. code-block:: yaml

  commands:
    mycommand:
      unix: "python ${PROJECT_DIR}/analyze.py"
      windows: "python %PROJECT_DIR%\analyze.py"
      description: "This command runs the analysis"

Environments and Channels
=========================

You can configure packages in a top level ``packages``
section of the ``kapsel.yml`` file, as we discussed earlier:

.. code-block:: yaml

  packages:
    - redis-py

You can also add specific conda channels to be searched for
packages:

.. code-block:: yaml

  channels:
    - conda-forge

``conda kapsel`` creates an environment in ``envs/default`` by
default. But if you prefer, you can have multiple named
environments available in the ``envs`` directory. To do that,
specify an ``env_specs:`` section of your ``kapsel.yml`` file:

.. code-block:: yaml

  env_specs:
    default:
      packages:
        - foo
        - bar
      channels:
        - conda-forge
    python27:
      description: "Uses Python 2 instead of 3"
      packages:
        - python < 3
      channels:
        - https://example.com/somechannel

An "environment spec" is a description of an environment,
describing the packages that the project requires to run.  By
default, environment specs are instantiated as actual Conda
environments in the ``envs`` directory inside your project.

In the above example we create two environment specs, which will
be instantiated as two environments, ``envs/default`` and
``envs/python27``.

To run a project using a specific env spec, use the ``--env-spec`` option:

.. code-block:: bash

  conda kapsel run --env-spec myenvname

https://github.com/Anaconda-Server/conda kapsel/issues/97

If you have top level ``channels`` or ``packages`` sections in
your ``kapsel.yml`` file (not in the ``env_specs:`` section),
those channels and packages are added to all environment
specs.

The default environment spec can be specified for each command,
like this:

.. code-block:: yaml

  commands:
    mycommand:
      unix: "python ${PROJECT_DIR}/analyze.py"
      windows: "python %PROJECT_DIR%\analyze.py"
      env_spec: my_env_spec_name


pip packages
============

Underneath any `packages:` section, you can add a `pip:`
section with a list of pip requirement specifiers.

.. code-block:: yaml

    packages:
       - condapackage1
       - pip:
         - pippackage1
         - pippackage2


Requiring environment variables to be set
=========================================

Anything in the ``variables:`` section of a ``kapsel.yml`` file
is considered an environment variable needed by your project.
When someone runs your project, ``conda kapsel`` asks
them to set these variables.

For example:

.. code-block:: yaml

  variables:
    - AMAZON_EC2_USERNAME
    - AMAZON_EC2_PASSWORD

Now in your script, you can ``os.getenv()`` these variables.

NOTE: This is a much better option than hardcoding passwords into your
script, which can be a security risk.


Variables that contain credentials
==================================

Variables that end in ``_PASSWORD``, ``_ENCRYPTED``,
``_SECRET_KEY``, or ``_SECRET`` are treated sensitively by
default. This means that if ``conda kapsel`` stores a value
for them in ``kapsel.yml`` or ``kapsel-local.yml`` or elsewhere,
that value is encrypted. NOTE: ``kapsel-local.yml`` stores and
encrypts the value that you enter when prompted.

To force a variable to be encrypted or not encrypted, add the
``encrypted`` option to it in ``kapsel.yml``, like this:

.. code-block:: yaml

  variables:
    # let's encrypt the password but not the username
    AMAZON_EC2_USERNAME: { encrypted: false }
    AMAZON_EC2_PASSWORD: { encrypted: true }

NOTE: The value of the environment variable is NOT encrypted
when passed to your script; the encryption happens only when we
save the value to a config file.


Variables with default values
=============================

If you make the ``variables:`` section a dictionary instead of a
list, you can give your variables default values. Anything
in the environment or in ``kapsel-local.yml`` overrides
these defaults. To omit a default for a variable, set
its value to either ``null`` or ``{}``.

For example::

.. code-block:: yaml

  variables:
    FOO: "default_value_of_foo"
    BAR: null # no default for BAR
    BAZ: {} # no default for BAZ
    # default as part of options dict, needed if you also
    # want to set some options such as 'encrypted: true'
    BLAH: { default: "default_value_of_blah" }
    BLARGH: { default: "default_value_of_blargh", encrypted: true }


Variables can have custom description strings
=============================================

A variable can have a 'description' field, which will be used in UIs
which display the variable.

For example:

.. code-block:: yaml

  variables:
    SALES_DB_PASSWORD: {
       description: "The password for the sales database, ask jim@example.com if you don't have one."
    }


Variables that are always set
=============================

``conda kapsel`` ensures that the following variables
are always set:

 * ``KAPSEL_DIR`` is set to the top level directory of your
   project
 * ``CONDA_ENV_PATH`` is set to the filesystem location of
   the current conda environment
 * ``PATH`` includes the binary directory from the current
   conda environment

These variables always exist, so for example to get a
file from your project directory, try this in your Python code
(notebook or script):

.. code-block:: python

  import os
  project_dir = os.getenv("PROJECT_DIR")
  my_file = os.path.join(project_dir, "my/file.txt")


Services
========

Services can be automatically started, and their address
can be provided to your code by using an environment variable.

For example, you can add a services section to your ``kapsel.yml`` file:

.. code-block:: yaml

  services:
    REDIS_URL: redis

Now when someone else runs your project, ``conda kapsel``
offers to start a local instance of ``redis-server`` automatically.

There is also a long form of the above service configuration:

.. code-block:: yaml

  services:
    REDIS_URL: { type: redis }

and you can set a default and any options a service may have:

.. code-block:: yaml

  services:
    REDIS_URL:
       type: redis
       default: "redis://localhost:5895"

Right now, there's only one supported service (Redis) as a
demo. However, we hope to support more soon.


File Downloads
==============

The ``downloads:`` section of the ``kapsel.yml`` file lets you define
environment variables that point to downloaded files. For example:

.. code-block:: yaml

  downloads:
    MYDATAFILE:
      url: http://example.com/bigdatafile
      sha1: da39a3ee5e6b4b0d3255bfef95601890afd80709

Rather than `sha1`, you can use whatever integrity hash you have;
supported hashes are ``md5``, ``sha1``, ``sha224``, ``sha256``,
``sha384``, ``sha512``.

NOTE: The download is checked for integrity ONLY if you specify a hash.

You can also specify a filename to download to, relative to your
project directory. For example:

.. code-block:: yaml

  downloads:
    MYDATAFILE:
      url: http://example.com/bigdatafile
      filename: myfile.csv

This downloads to ``myfile.csv``, so if your project is in
``/home/mystuff/foo`` and the download succeeds, ``MYDATAFILE``
is set to ``/home/mystuff/foo/myfile.csv``.

If you do not specify a filename, ``conda kapsel`` picks a
reasonable default based on the URL.

To avoid the automated download, it's also possible for someone to
run your project with an existing file path in the environment;
on Linux or Mac, that looks like:

.. code-block:: bash

  MYDATAFILE=/my/already/downloaded/file.csv conda kapsel run

Conda can auto-unzip a zip file as it is downloaded.  This is the
default if the the URL path ends in ".zip" unless the filename
also ends in ".zip". For URLs that do not end in ".zip", or to
change the default, you can specify the "unzip" flag:

.. code-block:: yaml

  downloads:
    MYDATAFILE:
      url: http://example.com/bigdatafile
      unzip: true

The ``filename`` is used as a directory and the zip file is unpacked
into the same directory, unless the zip contains a
single file or directory with the same name as ``filename``. In that
case, then the two are consolidated.

EXAMPLE: If your zip file contains a single directory
``foo`` with file ``bar`` inside that, and you specify downloading
to filename ``foo``, then you'll get ``KAPSEL_DIR/foo/bar``, not
``KAPSEL_DIR/foo/foo/bar``.


Describing the Project
======================

By default, Conda names your project with the same name as the
directory in which it is located. You can give it a different name
though in ``kapsel.yml``:

.. code-block:: yaml

  name: myproject

You can also have an icon file, relative to the project directory:

.. code-block:: yaml

  icon: images/myicon.png


No need to edit ``kapsel.yml`` directly
========================================

You can edit ``kapsel.yml`` with the ``conda kapsel`` command.

To add a download to ``kapsel.yml``:

.. code-block:: bash

  conda kapsel add-download MYFILE http://example.com/myfile

To add a package:

.. code-block:: bash

  conda kapsel add-packages redis-py

To ask for a running Redis instance:

.. code-block:: bash

  conda kapsel add-service redis


Fallback to meta.yaml
=====================

If you package your project with conda, you may have some
information already in ``conda.recipe/meta.yaml``;
``conda kapsel`` uses some of this information too, so you
do not need to duplicate this information in ``kapsel.yml``.

``conda kapsel`` currently reads these fields in ``meta.yaml``:

 * `package: name:`
 * `app: entry:`
 * `app: icon:`

For more about ``meta.yaml`` see http://conda.pydata.org/docs/building/meta-yaml.html
