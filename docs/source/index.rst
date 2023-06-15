=====
Conda
=====

.. figure::  /img/conda_logo.svg
   :align: center
   :width: 50%

   ..

|

:emphasis:`Package, dependency and environment management for any
language---Python, R, Ruby, Lua, Scala, Java, JavaScript, C/ C++,
FORTRAN`

Conda is an open-source package management system and environment
management system that runs on Windows, macOS, and Linux. Conda
quickly installs, runs, and updates packages and their dependencies.
Conda easily creates, saves, loads, and switches between environments
on your local computer. It was created for Python programs but it
can package and distribute software for any language.

Conda as a package manager helps you find and install packages.
If you need a package that requires a different version of
Python, you do not need to switch to a different environment
manager because conda is also an environment manager. With just
a few commands, you can set up a totally separate environment to
run that different version of Python, while continuing to run
your usual version of Python in your normal environment.

In its default configuration, conda can install and manage the
over 7,500 packages at repo.anaconda.com that are built, reviewed,
and maintained by Anaconda\ |reg|.

Conda can be combined with continuous integration systems, such
as GitHub Actions, to provide frequent, automated testing
of your code.

The conda package and environment manager is included in all versions of
:ref:`Anaconda <anaconda-glossary>`\ |reg|,
:ref:`Miniconda <miniconda-glossary>`, and
`Anaconda Repository <https://docs.continuum.io/anaconda-repository/>`_.
Conda is also included in `Anaconda Enterprise
<https://www.anaconda.com/enterprise/>`_, which provides on-site enterprise
package and environment management for Python, R, Node.js, Java, and other
application stacks. Conda is also available on
`conda-forge <https://anaconda.org/conda-forge/conda>`_, a community channel.
You may also get conda on `PyPI <https://pypi.org/>`_, but
that approach may not be as up to date.

.. toctree::
   :hidden:
   :maxdepth: 1
   :titlesonly:

   user-guide/index
   configuration
   api/index
   commands
   glossary
   dev-guide/index
   release-notes

.. |reg|    unicode:: U+000AE .. REGISTERED SIGN
