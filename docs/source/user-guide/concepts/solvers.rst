.. _concepts-solvers:

=======
Solvers
=======

When you install, update, or remove packages, conda must determine which
package versions can work together in the same environment. The component that
does this is called a **solver**. This page explains what solver plugins are,
which solvers conda supports, and how to check and switch between them.

.. _what-are-solver-plugins:

What are solver plugins?
========================

Conda does not have a single, built-in solver. Instead, solvers are provided
through a plugin system. Each solver is a separate package that registers
itself with conda, which means you can:

* Use a different solver without changing conda itself.
* Install more than one solver side by side.
* Configure one solver globally and switch to another for a single command.

Because solvers are independent packages, each one has its own documentation,
release schedule, and issue tracker. See the links in each section for
solver-specific details.

.. _solvers-available:

Available solvers
=================

The following table summarizes the solvers that work with conda:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Solver
     - Package
     - Status
   * - :ref:`rattler <solvers-rattler>`
     - ``conda-rattler-solver``
     - Default since conda 26.10.0
   * - :ref:`libmamba <solvers-libmamba>`
     - ``conda-libmamba-solver``
     - Available alternative solver
   * - :ref:`pycosat (classic) <solvers-pycosat>`
     - ``conda-pycosat-solver``
     - Available alternative solver

.. note::

   The default solver can change between conda releases. An explicit solver
   setting continues to take precedence when you upgrade conda. To see which
   solver your installation uses, follow the steps in
   :ref:`Check which solver is activated <solvers-check>`.

.. _solvers-rattler:

rattler
-------

The ``rattler`` solver plugin is provided by the ``conda-rattler-solver`` package.
It uses the `Resolvo <https://github.com/prefix-dev/resolvo>`_ dependency resolution
engine through `rattler <https://github.com/conda/rattler>`_, a collection of Rust
libraries for working with conda packages.

The plugin solves environments faster than libmamba, with the largest improvements on
large or heavily constrained environments. Starting with conda 26.10.0,
``rattler`` is the default solver.

`conda-rattler-solver documentation <https://conda.github.io/conda-rattler-solver/>`_

.. _solvers-libmamba:

libmamba
--------

The libmamba solver is provided by the ``conda-libmamba-solver`` package. It
uses the solving engine from the mamba project and is available as an alternative
solver in conda. This solver delegates to the C/C++ ``libsolv`` library,
which gives it a low memory footprint, fast resolve times, and clear error
messages that identify conflicting constraints directly.

`conda-libmamba-solver documentation <https://conda.github.io/conda-libmamba-solver>`_

.. _solvers-pycosat:

pycosat
-------

The pycosat solver is provided by the ``conda-pycosat-solver`` package.
This solver has powered conda since conda's first release and is based on the
``pycosat`` Python bindings for the PicoSAT library.

.. note::

   ``classic`` is a supported alias for ``pycosat``. Both names select the same
   solver, so existing ``solver: classic`` settings and ``--solver=classic``
   commands continue to work.

Choose the pycosat solver when backwards compatibility with existing long-lived environments
is important and you need solve results that match the original conda behavior exactly.

`conda-pycosat-solver documentation <https://conda.github.io/conda-pycosat-solver>`_

.. _solvers-check:

Checking which solver is activated
==================================

To see which solver conda currently has configured, run:

.. code-block:: bash

   conda config --show solver

The command prints the name of the configured solver, such as ``rattler``. To
see which configuration file the setting comes from, run:

.. code-block:: bash

   conda config --show-sources

.. _solvers-change:

Changing your solver
====================

To change the solver conda uses for all commands, set the ``solver``
configuration option:

.. code-block:: bash

   conda config --set solver rattler

Replace ``rattler`` with ``libmamba`` or ``pycosat`` to use a different solver.
Conda saves the setting in your ``.condarc`` file. For more information on your
``.condarc`` file, see :doc:`Using the .condarc conda configuration file <../configuration/use-condarc>`.

.. note::

   The solver plugin must be installed in your ``base`` environment before you
   can select it. For example:

   .. code-block:: bash

      conda plugins install conda-rattler-solver

To return to the default solver, remove the custom solver setting:

.. code-block:: bash

   conda config --remove-key solver

.. _solvers-single-command:

Use a solver for a single command
=================================

To try a different solver without changing your configuration, use the
``--solver`` flag with ``conda install``, ``conda create``, or
``conda update``:

.. code-block:: bash

   conda create --name test-env --solver rattler numpy

This approach is useful for comparing solvers or working around a problem with your
default solver while you troubleshoot.

.. _solvers-issues:

Report issues
=============

Where to report a problem depends on where it occurs. Solver plugins are
developed separately from conda, so report issues in the repository for the
solver you are using:

* **rattler:** `conda-rattler-solver issues <https://github.com/conda/conda-rattler-solver/issues>`_
* **libmamba:** `conda-libmamba-solver issues <https://github.com/conda/conda-libmamba-solver/issues>`_
* **pycosat:** `conda-pycosat-solver issues <https://github.com/conda/conda-pycosat-solver/issues>`_

If you aren't sure whether a problem is caused by the solver or by conda
itself, try the same command with a different solver using the ``--solver``
option (see :ref:`solvers-single-command`).

If the result changes, the problem is likely in the solver. Otherwise,
report it in the `conda issue tracker <https://github.com/conda/conda/issues>`_.
