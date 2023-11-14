===================
Conda Documentation
===================

Welcome to conda's documentation! Conda provides package, dependency and environment
management for any language. Here, you will find everything you need to get started
using conda in your own projects.

Install  :octicon:`download;1em;sd-text-primary`
................................................

We recommend the following methods to install conda:

.. tab-set::

    .. tab-item:: Windows :fab:`windows`

        .. grid:: 2

            .. grid-item::

                Miniconda installer for **Windows x86 64-bit**:

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
                    :color: primary

                    Download :octicon:`download`

    .. tab-item:: MacOS :fab:`apple`

        .. grid:: 2

            .. grid-item::

                Miniconda installer for **MacOS x86 64-bit**:

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.pkg
                    :color: primary

                    Download :octicon:`download`

            .. grid-item::

                Miniconda installer for **MacOS M1 64-bit**:

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg
                    :color: primary

                    Download :octicon:`download`

    .. tab-item:: Linux :fab:`linux`

        .. grid:: 2

            .. grid-item::

                Miniconda installer for **Linux x86 64-bit**:

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
                    :color: primary

                    Download :octicon:`download`

    .. tab-item:: Homebrew :fa:`beer-mug-empty`

        Run the following `Homebrew <https://brew.sh/>`_ command:

        .. code-block:: bash

            brew install miniconda

    .. tab-item:: Chocolatey :octicon:`terminal` :fab:`windows`

        Run the following `Chocolatey <https://chocolatey.org/>`_ command:

        .. code-block:: bash

            choco install miniconda3


.. raw:: html

    <p class="text-muted text-small">For more detailed instructions, see <a href="https://docs.conda.io/projects/miniconda/en/latest/">Miniconda's installation guide</a></p>

New to conda? :octicon:`rocket;1em;sd-text-primary`
...................................................

If you are new to conda, we first recommend the following articles:

.. grid::
    :gutter: 2

    .. grid-item-card:: Getting started guide
        :link: /user-guide/getting-started
        :link-type: doc

        Learn the basics of using conda such as creating and adding packages to environments

    .. grid-item-card:: Managing environments
        :link: /user-guide/tasks/manage-environments
        :link-type: doc

        Go in depth about environments and best practices for using them in your projects

.. seealso::

    Want to get even more in-depth training on how to use conda for free? Check out Anaconda's
    `free course on conda basics <https://learning.anaconda.cloud/conda-basics>`_.

Other useful resources :octicon:`light-bulb;1em;sd-text-primary`
......................................................................

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: Command reference
        :link: /commands/index
        :link-type: doc

        Full reference for all standard commands and options

    .. grid-item-card:: Cheatsheets
        :link: /user-guide/cheatsheet
        :link-type: doc

        Get the latest cheatsheet for commonly used commands

    .. grid-item-card:: Configuring conda
        :link: /user-guide/configuration/use-condarc
        :link-type: doc

        Learn about the various ways conda's behavior can be configured

    .. grid-item-card:: Glossary
        :link: /glossary
        :link-type: doc

        Important vocabulary to know when working with conda


Contributors welcome :octicon:`git-pull-request;1em;sd-text-primary`
....................................................................

Conda is an open source project and always welcomes new contributions.
Please read the following guides to get started developing conda and
making your own contributions.

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: Contributing 101
        :link: /dev-guide/contributing
        :link-type: doc

        Learn more about how the conda project is managed and how to contribute

    .. grid-item-card:: Development environment
        :link: /dev-guide/development-environment
        :link-type: doc

        Follow this guide to get your own development environment set up.



.. toctree::
   :hidden:
   :maxdepth: 1
   :titlesonly:

   user-guide/index
   configuration
   commands/index
   release-notes
   glossary
   dev-guide/index
   api/index

.. |reg|    unicode:: U+000AE .. REGISTERED SIGN
