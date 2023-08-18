===============
Writing Tests
===============

This section contains a series of guides and guidelines for writing tests
in the ``conda`` repository.

----

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

----

General Guidelines
==================

* `Preferred test style (pytest)`_
* `Organizing tests`_
* `The "conda.testing" module`_
* `Adding new fixtures`_
* `The context object`_

.. note::
   It should be noted that existing tests may deviate
   from these guidelines, and that is okay. These guidelines are here to inform how we
   would like all new tests to look and function.

Preferred test style (pytest)
-----------------------------
Although our codebase includes class-based ``unittest`` tests, our preferred
format for all new tests are ``pytest`` style tests. These tests are written using
functions and handle the setup and teardown of context for tests using fixtures.
We recommend familiarizing yourself with ``pytest`` first before attempting to
write tests for ``conda``. Head over to their `Getting Started Guide <https://docs.pytest.org/en/stable/getting-started.html>`_
to learn more.

Organizing tests
----------------
Tests should be organized in a way that mirrors the main ``conda`` module.
For example, if you were writing a test for a function in
``conda/base/context.py``, you would place this test in ``tests/base/test_context.py``.

The "conda.testing" module
----------------------------
This is a module that contains anything that could possibly help with
writing tests, including fixtures, functions, and classes. Feel free to
make additions to this module as you see fit, but be mindful of organization.
For example, if your testing utilities are primarily only for the ``base`` module
considering storing these in ``conda.testing.base``.

Adding new fixtures
-------------------
For fixtures that have a very limited scope or purpose, it is okay to define these
alongside the tests themselves. However, if these fixtures could be used across multiple
tests, then they should be saved in a separate ``fixtures.py`` file. The ``conda.testing``
module already contains several of these files.

If you want to add new fixtures within a new file, be sure to add a reference to this module in
``tests/conftest.py::pytest_plugins``. This is our preferred way of making
fixtures available to our tests. Because of the way these are included in the
environment, you should be mindful of naming schemes and choose ones that likely will not
collide with each other. Consider using a prefix to achieve this.

The context object
------------------
The context object in ``conda`` is used as a singleton. This means that everytime the ``conda``
command runs, only a single object is instantiated. This makes sense as it holds all the configuration
for the program and re-instantiating it or making multiple copies would be inefficient.

Where this causes problems is during tests where you may want to run ``conda`` commands potentially
hundreds of times within the same process. Therefore, it is important to always reset this object
to a fresh state when writing tests.

This can be accomplished by using the ``reset_context`` function, which also lives in the
``conda.base.context`` module. The following example shows how you would modify the context
object and then reset it using the ``reset_conda_context`` ``pytest`` fixture:

.. code-block:: python

   import os
   import tempfile

   from conda.base.context import reset_context, context
   from conda.testing.fixtures import reset_conda_context

   TEST_CONDARC = """
   channels:
     - test-channel
   """


   def test_that_uses_context(reset_conda_context):
       # We first created a temporary file to hold our test configuration
       with tempfile.TemporaryDirectory() as tempdir:
           condarc_file = os.path.join(tempdir, "condarc")

           with open(condarc_file, "w") as tmp_file:
               tmp_file.write(TEST_CONDARC)

           # We use the reset_context function to load our new configuration
           reset_context(search_path=(condarc_file,))

           # Run various test assertions, below is an example
           assert "test-channel" in context.channels


Using this testing fixture ensures that your context object is returned to the way it was
before the test. For this specific test, it means that the ``channels`` setting will be returned to its
default configuration. If you ever need to manually reset the context during a test, you can do so by manually
invoking the ``reset_context`` command like in the following example:

.. code-block:: python

   from conda.base.context import reset_context


   def test_updating_context_manually():
       # Load some custom variables into context here like above...

       reset_context()

       # Continue testing with a fresh context...
