===================
Conda Documentation
===================

Welcome to conda's documentation! Conda provides package, dependency, and environment
management for any language. Here, you will find everything you need to get started
using conda in your own projects.

Install  :octicon:`download;1em;sd-text-primary`
................................................

We recommend the following methods to install conda:

.. tab-set::

    .. tab-item:: Windows :fab:`windows`

        Miniconda installer for:

        .. grid:: 2

            .. grid-item::

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
                    :color: primary

                    Windows x86 64-bit :octicon:`download`

    .. tab-item:: macOS :fab:`apple`

        Miniconda installer for:

        .. grid:: 2

            .. grid-item::

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg
                    :color: primary

                    macOS with Apple Silicon 64-bit :octicon:`download`

            .. grid-item::

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.pkg
                    :color: primary

                    macOS with Intel CPU 64-bit :octicon:`download`

    .. tab-item:: Linux :fab:`linux`

        Miniconda installer for:

        .. grid:: 2

            .. grid-item::

                .. button-link:: https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
                    :color: primary

                    Linux x86 64-bit :octicon:`download`

    .. tab-item:: Homebrew :fa:`beer-mug-empty`

        Run the following `Homebrew <https://brew.sh/>`_ command:

        .. code-block:: bash

            brew install miniconda

.. raw:: html

    <p class="text-small">For more detailed instructions, see <a href="https://docs.anaconda.com/free/miniconda/">Miniconda's installation guide</a></p>

New to conda? :octicon:`rocket;1em;sd-text-primary`
...................................................

If you are new to conda, we first recommend the following articles:

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Getting started guide :octicon:`rocket;1em;sd-text-primary`
        :link: /user-guide/getting-started/
        :link-type: doc

        Learn the basics of using conda such as creating and adding packages to environments

    .. grid-item-card:: Managing environments :octicon:`file-submodule;1em;sd-text-primary`
        :link: /user-guide/tasks/manage-environments/
        :link-type: doc

        Learn more about environments and best practices for using them in your projects

.. seealso::

    Want to get even more in-depth training on how to use conda for free? Check out Anaconda's
    `free course on conda basics <https://learning.anaconda.cloud/conda-basics>`_.

Other useful resources :octicon:`light-bulb;1em;sd-text-primary`
......................................................................

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Command reference :octicon:`terminal;1em;sd-text-primary`
        :link: /commands/index/
        :link-type: doc

        Full reference for all standard commands and options

    .. grid-item-card:: Cheatsheets :octicon:`note;1em;sd-text-primary`
        :link: /user-guide/cheatsheet/
        :link-type: doc

        Get the latest cheatsheet for commonly used commands

    .. grid-item-card:: Configuring conda :octicon:`gear;1em;sd-text-primary`
        :link: /user-guide/configuration/use-condarc/
        :link-type: doc

        Learn about the various ways conda's behavior can be configured

    .. grid-item-card:: Glossary :octicon:`book;1em;sd-text-primary`
        :link: /glossary/
        :link-type: doc

        Important vocabulary to know when working with conda


Contributors welcome :octicon:`git-pull-request;1em;sd-text-primary`
....................................................................

Conda is an open source project and always welcomes new contributions.
Please read the following guides to get started developing conda and
making your own contributions.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Contributing 101 :octicon:`people;1em;sd-text-primary`
        :link: /dev-guide/contributing/
        :link-type: doc

        Learn more about how the conda project is managed and how to contribute

    .. grid-item-card:: Development environment :octicon:`file-code;1em;sd-text-primary`
        :link: /dev-guide/development-environment/
        :link-type: doc

        Follow this guide to get your own development environment set up



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
