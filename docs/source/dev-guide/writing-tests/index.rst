===============
Writing Tests
===============

This section contains a series of guides and guidelines for writing tests
in the conda repository.

.. raw:: html

   <hr>

Guides
======

:doc:`integration-tests`
This guide gives an overview of how to write integration tests using full
command invocation. It also covers creating fixtures to use with these types
of tests.

.. toctree::
   :hidden:
   :maxdepth: 1

   integration-tests

.. raw:: html

   <hr>

General Guidelines
==================

* `Preferred test style (pytest)`_
* `Organizing tests`_
* `The "conda.testing" module`_
* `Adding new fixtures`_

.. note::
   It should be noted that existing tests may deviate
   from these guidelines, and that is okay. These guidelines are here to inform how we
   would like all new tests to look and function.

Preferred test style (pytest)
-----------------------------
Although our codebase includes class-based unittest tests, our preferred
format for all new tests are pytest style tests. These tests are written using
functions and handle the setup and teardown of context for tests using fixtures.
We recommend familiarizing yourself with pytest first before attempting to
write tests for conda. Head over to their `Getting Started Guide <https://docs.pytest.org/en/stable/getting-started.html>`_
to learn more.

Organizing tests
----------------
Tests should be organized in a way that mirrors the main ``conda`` module.
For example, if you were writing a test for a function in
``conda/base/context.py``, you would place this test in ``tests/base/test_context.py``.

The "conda.testing" module
----------------------------
This is a module that contains anything that could possibly help with
writing tests, including fixtures, functions and classes. Feel free to
make additions to this module as you see fit, but be mindful of organization.
For example, if your testing utilities are primarily only for the ``base`` module
considering storing these in ``conda.testing.base``.

Adding new fixtures
-------------------
For fixtures that have a very limited scope or purpose, it is okay to define these
alongside the tests themselves. But, if these fixtures could be used across multiple
tests, they should be saved in a separate ``fixtures.py`` file. The ``conda.testing``
module already contains several of these files.

If you want to add new fixtures within a new file, be sure to add a reference to this module in
``tests/conftest.py::pytest_plugins``. This is a our preferred way of making
fixtures available to our tests. Because of the way these are included in the
environment, you should be mindful of naming schemes and choose ones that likely will not
collide with each other. Consider using a prefix to achieve this.
