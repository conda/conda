===============
Developer guide
===============

Welcome to the conda developer guide. Whether you are fixing a bug, adding a new feature,
writing a plugin, or diving deep into conda's internals, this guide has everything you need
to get started and contribute effectively.

Getting started :octicon:`rocket;1em;sd-text-primary`
.....................................................

New to conda development? Start here.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Contributing 101 :octicon:`people;1em;sd-text-primary`
        :link: contributing
        :link-type: doc

        Learn how the conda project is managed, how to open issues and pull requests,
        and what to expect from the review process.

    .. grid-item-card:: Development environment :octicon:`file-code;1em;sd-text-primary`
        :link: development-environment
        :link-type: doc

        Follow this guide to set up a local development environment and run conda
        from source.

Architecture & internals :octicon:`project;1em;sd-text-primary`
...............................................................

Understand how conda is structured and how its most complex subsystems work.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Architecture :octicon:`database;1em;sd-text-primary`
        :link: architecture
        :link-type: doc

        A high-level overview of conda's architecture, its major components, and how
        they interact with each other.

    .. grid-item-card:: Deep dives :octicon:`telescope;1em;sd-text-primary`
        :link: deep-dives/index
        :link-type: doc

        Detailed explorations of particularly complex subsystems such as the solver,
        activation, context, and logging.

Extending conda :octicon:`plug;1em;sd-text-primary`
....................................................

Build on top of conda using its plugin system or consult the formal specifications.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Plugins :octicon:`plug;1em;sd-text-primary`
        :link: plugins/index
        :link-type: doc

        Learn how to extend and customize conda's behavior using the plugin system,
        including hooks for solvers, subcommands, auth handlers, and more.

    .. grid-item-card:: Specifications :octicon:`file;1em;sd-text-primary`
        :link: specs/index
        :link-type: doc

        Formal specifications for conda internals, including solver state and other
        components.

Contributing & quality :octicon:`heart;1em;sd-text-primary`
............................................................

Guides for writing tests, managing deprecations, and cutting releases.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: Writing tests :octicon:`beaker;1em;sd-text-primary`
        :link: writing-tests/index
        :link-type: doc

        Guidelines and guides for writing unit and integration tests, using the HTTP
        test server, and testing on Windows with AppLocker.

    .. grid-item-card:: Deprecations :octicon:`alert;1em;sd-text-primary`
        :link: deprecations
        :link-type: doc

        Learn the conda deprecation policy and how to mark APIs and behaviors as
        pending deprecated, deprecated, or removed.

    .. grid-item-card:: Releasing :octicon:`tag;1em;sd-text-primary`
        :link: releasing
        :link-type: doc

        Step-by-step instructions for preparing and publishing a new conda release,
        including the CalVer versioning scheme.

API reference :octicon:`code;1em;sd-text-primary`
..................................................

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: API reference :octicon:`code;1em;sd-text-primary`
        :link: /dev-guide/api
        :link-type: doc

        Auto-generated API documentation for all public modules, classes, and
        functions in the conda package.

.. toctree::
   :hidden:
   :maxdepth: 2
   :titlesonly:

   architecture
   contributing
   development-environment
   deep-dives/index
   writing-tests/index
   deprecations
   releasing
   plugins/index
   specs/index
