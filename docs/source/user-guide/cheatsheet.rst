==========
Cheatsheet
==========

The conda cheatsheet contains the most important information about using conda, such as basic commands for creating and managing environments, installing packages, and importing and exporting environments.

See the :cheatsheet-pdf:`conda cheatsheet` for a PDF version.

..
    Maintainers! The cheatsheet PDF is generated from the tables below every
    time the documentation is built (see the "conda_cheatsheet" extension),
    so there is no list of versions or symlink to update.

    The PDFs in "cheatsheets/" (conda-25.3.1.pdf, conda-24.4.0.pdf,
    conda-4.14.pdf, conda-4.12.pdf and conda-4.6.pdf) are intentionally no
    longer listed on this page. They are only kept so that links to them,
    which are published as "_downloads/<hash>/conda-*.pdf", keep working.
    Do not delete them.

Quickstart
==========

.. tip::

   It is recommended to create a new environment for any new project or workflow.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/quickstart.csv

Channels and Packages
=====================

.. tip::

   Package dependencies and platform specifics are automatically resolved when using conda.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/channels-and-packages.csv

Working with Conda Environments
===============================

.. tip::

   List environments at the beginning of your session. Environments with an asterisk are active.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/working-with-environments.csv

Environment Management
======================

.. tip::

   Specifying the environment name confines conda commands to that environment.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/environment-management.csv

Exporting Environments
======================

.. tip::

   Name your export file after your environment to preserve your environment name.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/exporting-environments.csv

Importing Environments
======================

.. tip::

   When importing an environment, conda resolves platform and package specifics.

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/importing-environments.csv

Additional Hints
================

.. csv-table::
    :widths: 42 58
    :header-rows: 0
    :file: cheatsheets/additional-hints.csv
