.. _install-pypi-packages-with-conda:

Installing packages from PyPI with conda
========================================

.. note::
   The ``conda-pypi`` channel is free to use for all users. This channel is not
   subject to the licensing requirements or payment obligations described in
   Section 1 of the `Anaconda Terms of Service <https://www.anaconda.com/legal/terms/terms-of-service>`_.

In conda version 26.9 and later, you can use the ``conda-pypi`` channel to
install supported pure Python wheels from the Python Package Index (PyPI)
alongside conda packages directly with ``conda install``.

.. dropdown:: What does the ``conda-pypi`` channel do?

   The ``conda-pypi`` channel, a channel maintained by Anaconda and hosted for free
   on anaconda.org, indexes all pure Python wheels from the public PyPI index. The
   channel repodata is generated from package metadata obtained from PyPI and
   converted into a format conda understands, so the reliability and security of packages available
   through ``conda-pypi`` matches that of PyPI directly.

   When you add this channel to your conda configuration, conda can resolve
   and install those packages alongside packages from conda channels like
   ``conda-forge`` or ``defaults`` in a single operation. The channel repodata
   tells conda what packages are available and at what versions. When you install a
   package, conda fetches the wheel directly from PyPI at install time. This is by
   design and keeps the channel lightweight, but it means you need a PyPI connection
   at install time.

   One important thing to note is that **this is not a pip replacement**. Conda still
   manages the environment, the solver still handles the full dependency
   graph, and the result is a reproducible, exportable conda environment. Using
   ``pip install`` directly inside conda environments can work initially, but
   conda loses track of pip-installed packages, making future environment updates
   and installs unreliable. For more information on using pip with conda, see our blog
   `Conda and pip are two ecosystems, not just tools <https://conda.org/blog/2026-05-07-conda-and-pip-ecosystems>`_.

Prerequisites
-------------

The ``conda-pypi`` workflow requires the following:

- **conda 26.9 or later:**

  Check your version:

  .. code-block:: bash

      conda --version

  If necessary, update conda:

  .. code-block:: bash

      conda self update

- **Rattler solver:**

  Set the rattler solver as your default solver:

  .. code-block:: bash

      conda config --set solver rattler

Setting up the conda-pypi channel
----------------------------------

To make supported packages from PyPI available to conda, add the
``conda-pypi`` channel to your conda configuration (``.condarc``) file.
Append it after your existing channels to give it a lower channel priority:

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
the full dependency graph across all configured channels, so packages from PyPI
and conda channels can be installed together in a single command.

Find available packages
~~~~~~~~~~~~~~~~~~~~~~~~

To check whether a package is available through ``conda-pypi``:

.. code-block:: bash

   conda search conda-pypi::<package-name>

Install packages from PyPI and conda channels together
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   conda install <conda-forge-package> <conda-pypi-package>

When a package is available from both ``conda-forge`` and ``conda-pypi``,
conda selects a build according to your channel priority setting and
the environment's dependency requirements.

You can also use ``conda create`` with packages from PyPI:

.. code-block:: bash

   conda create --name myenv python=3.12 <conda-forge-package> <conda-pypi-package>

Install with extras support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extras are named groups of optional dependencies. When you request an extra,
its dependencies are resolved together with the package's regular dependencies.
For full details, see `CEP 44 <https://conda.org/learn/ceps/cep-0044>`_.

Use the following syntax to request extras:

.. code-block:: bash

   # Single extra
   conda install 'package[extras="EXTRA"]'

   # Multiple extras (comma-separated string)
   conda install 'package[extras="EXTRA1,EXTRA2"]'

   # Multiple extras (list syntax)
   conda install 'package[extras=["EXTRA1","EXTRA2"]]'

For example, to install ``httpx`` with its ``http2`` and ``cli`` extras:

.. code-block:: bash

   conda install 'httpx[extras="http2,cli"]'

.. note::

   Extra names are case-sensitive and must match the pattern
   ``[a-z0-9_.+-]{1,64}``. Requesting an extra that is not defined in a
   package has no effect and doesn't produce an error.

Disable the conda-pypi workflow
---------------------------------

If you want to stop using the ``conda-pypi`` channel, remove it from your
configuration:

.. code-block:: bash

   conda config --remove channels conda-pypi

Suppress the conda-pypi suggestion tip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To suppress the suggestion about the ``conda-pypi`` channel shown when
conda newly installs pip into an environment, set the following
configuration option:

.. code-block:: bash

   conda config --set plugins.conda_pypi_pip_warning false

Limitations and security considerations
---------------------------------------

The security posture of this workflow is equivalent to using pip or other PyPA
tools to install from the public PyPI index directly. Packages are fetched from
PyPI at install time. Conda does not re-sign or additionally vet the wheels. Keep
the following limitations in mind:

* **Public PyPI only.** The ``conda-pypi`` channel indexes packages from PyPI.
  It does not include packages from private or alternative package indexes
  (such as a corporate artifact repository).
* **No additional vetting beyond PyPI.** The ``conda-pypi`` channel does not
  perform additional security scanning beyond what PyPI provides. Using the
  :ref:`--exclude-newer flag <installing-packages-with-an-upload-cutoff>`
  is recommended as a lightweight mitigation for supply-chain risk.
* **conda client only.** Supported in the conda CLI. Support in other clients
  (mamba, micromamba, and so on) is under active CEP discussion.
* **Pure Python wheels only.** Packages with compiled extensions must come
  from conda channels.
* **rattler solver required.** The classic conda solver is not supported for
  this workflow.
* **PyPI connection required at install time.** The channel stores metadata
  only. Wheels are fetched from PyPI during installation.

Troubleshooting
---------------

Packages not found in ``conda-pypi``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

If either is below the minimum required version
(26.9 for ``conda`` and 0.1.1 for ``conda-rattler-solver``), update them:

.. code-block:: bash

   conda self update

.. code-block:: bash

   conda install --name base conda-rattler-solver

Additional resources
--------------------

* `conda-pypi plugin documentation <https://conda.github.io/conda-pypi/>`_ —
  advanced configuration and workflows
* :doc:`manage-channels` — channel priority and configuration reference
