===========
Performance
===========

Conda's performance can be affected by a variety of things.
Unlike many package managers, Anaconda’s repositories generally
don’t filter or remove old packages from the index. This allows old
environments to be easily recreated. However, it does mean that the
index metadata is always growing, and thus conda becomes slower as the
number of packages increases.

How a package is installed
==========================

While you are waiting, conda is doing a lot of work installing the
packages. At any point along these steps, performance issues may arise.

Conda follows these steps when installing a package:

#. Downloading and processing index metadata.
#. Reducing the index.
#. Expressing the package data and constraints as a SAT problem.
#. Running the solver.
#. Downloading and extracting packages.
#. Verifying package contents.
#. Linking packages from package cache into environments.

Therefore, if you're experiencing a slowdown, evaluate the following questions
to identify potential causes:

* Are you creating a new environment or installing into an existing one?
* Does your environment have pip-installed dependencies in it?
* What channels are you using?
* What packages are you installing?
* Is the channel metadata sane?
* Are channels interacting in bad ways?

Improving conda performance
===========================

This section goes over some of the best practices we recommend for addressing performance challenges.

#. Make your package specifications more narrow.

   For example, instead of ``numpy``, we recommend ``numpy=1.15`` or, even better, ``numpy=1.15.4``.

#. Make sure you have libmamba set as your dependency solver. The conda libmamba solver was made the default solver in conda v23.9. It is a faster and more efficient solver than conda's classic solver, especially for large environments.

   To check which solver you have, run the following command:

   .. code-block:: shell

      conda config --show solver

   If libmamba is set as your solver, you will see the following:

   .. code-block:: shell

      solver: libmamba

   If you don't have libmamba set as your solver, follow these steps to enable it:

   #. Make sure ``conda-libmamba-solver`` is installed in your base environment:

      .. code-block:: shell

         conda install --name base conda-libmamba-solver

   #. Set libmamba as your default solver:

      .. code-block:: shell

         conda config --set solver libmamba

   .. tip::

      You can also use the libmamba solver temporarily when installing a package:

      .. code-block:: shell

         conda install --solver=libmamba package_name

.. _concepts-performance-channel-priority:

#. Use strict channel priority. This makes it so that if a package exists on a channel, conda ignores all packages with the same name on lower priority channels, dramatically reducing package search space and the use of improperly constrained pacakges.

   .. warning::

      Setting strict channel priority might make environments unsatisfiable. Learn more about :ref:`strict`.

   .. figure:: ../../img/strict-disabled.png
    :width: 50%
   .. figure:: ../../img/strict-enabled.png
    :width: 50%

   .. code-block:: shell

      conda config --set channel_priority strict

#. Enable sharded repodata. This splits your repodata into multiple small files and fetches only what is needed, which dramatically speeds up environment creation and updates. Learn more in `CEP 16 <https://conda.org/learn/ceps/cep-0016>`_.

   .. note::

      This option is currently available for conda-forge and prefix.dev for all channels as of March 2026.

   Follow these steps to opt-in to sharded repodata:

   #. Update conda-libmamba-solver, if needed:

      .. code-blocK:: shell

         conda install --name base "conda-libmamba-solver>=25.11.0"

   #. Set the ``use_sharded_repodata`` plugin to ``true``:

      .. code-block:: shell

         conda config --set plugins.use_sharded_repodata true
