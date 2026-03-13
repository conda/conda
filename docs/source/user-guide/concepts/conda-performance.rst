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

1. Make sure you have libmamba set as your solver. To check which solver you have, run the following command:

   .. code-block:: shell
      
      conda config --show solver
   
   To set libmamba as your default server:

   .. code-block:: shell

      conda config --set solver libmamba

   You can also use the libmamba solver temporarily when installing a package:

   .. code-block:: shell

      conda install --solver=libmamba package_name

.. _concepts-performance-channel-priority:

2. Use strict channel priority. This will improve performance by eliminating possible mixed repository solutions.

   Setting strict channel priority makes it so that if a package exists on a channel, conda will ignore all packages with the same name on lower priority channels. This can dramatically reduce package search space and reduces the use of improperly constrained packages. However, setting strict channel priority may make environments unsatisfiable. Learn more about :ref:`strict`.

   .. figure:: ../../img/strict-disabled.png
    :width: 50%
   .. figure:: ../../img/strict-enabled.png
    :width: 50%

   .. code-block:: shell

      conda config --set channel_priority strict

3. Enable sharded repodata.

   .. note::

      This option is available for conda-forge and prefix.dev for all channels.

   



    * Specifying very broad package specs?
        * Be more specific. Letting conda filter more candidates makes it faster.
          For example, instead of ``numpy``, we recommend ``numpy=1.15`` or, even better, ``numpy=1.15.4``.
        * If you are using R, instead of specifying only ``r-essentials``, specify ``r-base=3.5 r-essentials``.
    * Observing that an Anaconda or Miniconda installation is getting slower over time?
        * Create a fresh environment. As environments grow, they become harder
          and harder to solve. Working with small, dedicated environments can
          be much faster.
