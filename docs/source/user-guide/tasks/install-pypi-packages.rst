.. _install-pypi-packages-with-conda:

Installing PyPI packages with conda
====================================

In conda version 26.9 and later, you can use the ``conda-pypi`` channel to
install supported PyPI packages alongside regular conda packages directly 
with ``conda install``.

.. dropdown:: What does the ``conda-pypi`` channel do?

   The ``conda-pypi`` channel, a community-maintained channel that is hosted on
   anaconda.org, indexes pure Python wheels from the public PyPI index.
   When you add this channel to your conda configuration, conda can resolve
   and install those packages alongside packages from conda channels like
   ``conda-forge`` or ``defaults`` in a single operation.

   The ``conda-pypi`` channel repodata tells conda what packages are available and
   at what versions. When you install a package, conda fetches the wheel directly
   from PyPI at install time. This is by design and keeps the channel lightweight,
   but it means you need a PyPI connection at install time.

   One important thing to note is that **this is not a pip replacement**. Conda still
   manages the environment, the solver still handles the full dependency
   graph, and the result is a reproducible, exportable conda environment. Using
   ``pip install`` directly inside conda environments remains problematic and should
   be done with care. For more information on using pip with conda, see our blog
   `Conda and pip are two ecosystems, not just tools <https://conda.org/blog/2026-05-07-conda-and-pip-ecosystems>`_.

.. TODO: Add provenance information for the conda-pypi channel to the dropdown above: who created
      and maintains it, how it is governed, and how the channel repodata is
      generated. Confirm details with the team (conda GitHub org ownership,
      governance model, repodata generation process).

Prerequisites
-------------

The ``conda-pypi`` workflow requires the following:

- **conda 26.9 or later:**

  Check your version:

  .. code-block:: bash

      conda --version

  If necessary, update conda:

  .. code-block:: bash

      conda update conda

- **Rattler solver:**

  Set the rattler solver as your default solver:

  .. code-block:: bash

      conda config --set solver rattler

Setting up the conda-pypi channel
----------------------------------

To gain access to compatible PyPI packages, add the ``conda-pypi`` channel to
your conda configuration (``.condarc``) file. Append it *after* your existing
conda channels so that conda resolves packages from conda channels first and falls
back to ``conda-pypi`` for packages not available there:

.. code-block:: bash

   conda config --append channels conda-pypi

Your channel order in ``~/.condarc`` should look similar to this:

.. code-block:: yaml

   channels:
     - conda-forge
     - conda-pypi

.. dropdown:: Channel priority and ABI compatibility

   Normally, when mixing channels, strict channel priority is recommended
   to avoid ABI incompatibilities between compiled packages built in different
   environments. The ``conda-pypi`` channel contains only pure Python wheels,
   so there are no compiled binaries and, therefore, no ABI risk.

   Flexible priority (the default) also works correctly when pairing ``conda-pypi``
   with ``conda-forge`` or ``defaults``. For more on channel priority,
   see :ref:`channel-best-practices`.

Install packages
----------------

Before installing, you can check what is available in the ``conda-pypi`` channel
using ``conda search``. Once the channel is configured, ``conda install`` resolves
the full dependency graph across all configured channels, so conda and PyPI packages
can be installed together in a single command.

Find available packages
~~~~~~~~~~~~~~~~~~~~~~~~

To check whether a package is available through ``conda-pypi``:

.. code-block:: bash

   conda search --channel conda-pypi <package-name>

Install PyPI and conda packages together
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   conda install numpy requests

In this example, ``numpy`` comes from ``conda-forge`` (it has compiled extensions)
and ``requests`` comes from ``conda-pypi`` (it is a pure Python package). Conda
handles both in a single operation.

You can also use ``conda create`` with PyPI packages:

.. code-block:: bash

   conda create --name myenv python=3.12 numpy requests flask

Install with extras support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO: Confirm extras support syntax and status with team — currently in development

Extras (optional dependency groups defined in a package's metadata) are supported.
Use bracket syntax as you would with pip:

.. code-block:: bash

   conda install "httpx[http2]"

Manage your environment
-----------------------

The ``conda-pypi`` workflow produces a standard conda environment. All the usual
environment management commands work as expected. For more information on
environment management and package management, besides what is covered here,
see :doc:`manage-environments` and :doc:`manage-pkgs`.

List installed packages
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   conda list

Packages installed from ``conda-pypi`` appear in the output alongside packages from
other channels, with their channel source listed.

Export and recreate an environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Export an environment specification:

.. code-block:: bash

   conda env export > environment.yml

Recreate it on another machine (which also needs ``conda-pypi`` configured):

.. code-block:: bash

   conda env create --file environment.yml

Remove a package
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   conda remove <package-name>

.. _exclude-newer:

Control package age with ``--exclude-newer``
--------------------------------------------

The ``--exclude-newer`` flag tells conda to ignore package versions published after a
specified date, giving new releases a cooldown period before they are adopted in
your environment.

This flag can be used as a security measure. The time after a new release is
published is a common attack surface for supply-chain incidents, where a
malicious or broken version may be published before it is detected and pulled.
By setting a cutoff date, you reduce exposure to freshly published packages.

For example, if you use ``--exclude-newer 2025-08-01``, conda will only consider
package versions published on or before August 1, 2025. Any versions published
after that date will be ignored.

.. code-block:: bash

   conda install requests --exclude-newer 2025-08-01

.. TODO: Confirm flag name and exact syntax at GA

Pre-release versions
--------------------

.. TODO: Confirm pre-release handling with team.
   Tracking issue: https://github.com/conda/conda-pypi/issues/448

This section will document how to opt in to pre-release versions from
``conda-pypi``.

Disable the conda-pypi workflow
---------------------------------

If you want to stop using the ``conda-pypi`` channel, remove it from your
configuration:

.. code-block:: bash

   conda config --remove channels conda-pypi

Suppress the conda-pypi suggestion tip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to suppress the suggestion that conda displays when you install a 
package that is available through the ``conda-pypi`` channel, set the
following configuration option:

.. code-block:: bash

   conda config --set conda_pypi_warning false

.. TODO: Confirm exact config key name for suppressing the tip

Limitations and security considerations
---------------------------------------

The security posture of this workflow is equivalent to using pip or other PyPA
tools to install from the public PyPI index directly. Packages are fetched from
PyPI at install time; conda does not re-sign or additionally vet the wheels. Keep
the following limitations in mind:

* **Public PyPI only.** Private or alternative PyPI indexes (such as a corporate
  artifact repository) are not currently supported.
* **No additional vetting beyond PyPI.** The ``conda-pypi`` channel does not
  perform additional security scanning beyond what PyPI provides. Using the
  :ref:`--exclude-newer flag <exclude-newer>` is recommended as a lightweight
  mitigation for supply-chain risk.
* **conda client only.** Supported in the conda CLI. Support in other clients
  (mamba, micromamba, and so on) is under active CEP discussion.
* **Pure Python packages only.** Packages with compiled extensions must come
  from conda channels.
* **rattler solver required.** The classic conda solver is not supported for
  this workflow.
* **PyPI connection required at install time.** The channel stores metadata
  only; wheels are fetched from PyPI during installation.

Troubleshooting
---------------

Packages not found in ``conda-pypi``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``conda install`` or ``conda create`` fails with a ``PackagesNotFoundInChannelsError``
for a package you expect to be available through ``conda-pypi``, the most likely
cause is an outdated version of conda or the rattler solver.

For example:

.. code-block:: text

   PackagesNotFoundInChannelsError: The following packages are not available
   from current channels:
     - flask

   Current channels:
     - defaults
     - https://conda.anaconda.org/conda-pypi

To diagnose, check your conda and rattler-solver versions:

.. code-block:: bash

   conda --version

.. code-block:: bash

   conda list | grep rattler

.. TODO: Add minimum required rattler-solver version. Example output from the
   team's testing: ``conda-rattler-solver 0.1.1``. Confirm what the actual
   minimum is before publishing.

If either is below the minimum required version, update them:

.. code-block:: bash

   conda update conda

.. code-block:: bash

   conda install --name base rattler-solver

Additional resources
--------------------

* `conda-pypi plugin documentation <https://conda.github.io/conda-pypi/>`_ —
  advanced configuration and workflows
* :doc:`manage-channels` — channel priority and configuration reference
