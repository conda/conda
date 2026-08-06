===============
Developer guide
===============

Welcome to the conda developer guide. Whether you are fixing a bug, adding a new feature,
writing a plugin, or diving deep into conda's internals, this guide has everything you need
to get started and contribute effectively.

Getting started :octicon:`rocket;1em;sd-text-primary`
.....................................................

New to conda development? Start here.

.. glossary::

    :doc:`Contributing 101 <contributing>`
        Learn how the conda project is managed, how to open issues and pull requests,
        and what to expect from the review process.

    :doc:`Development environment <development-environment>`
        Follow this guide to set up a local development environment and run conda
        from source.

Architecture & internals :octicon:`project;1em;sd-text-primary`
...............................................................

Understand how conda is structured and how its most complex subsystems work.

.. glossary::

    :doc:`Architecture <architecture>`
        A high-level overview of conda's architecture, its major components, and how
        they interact with each other.

    :doc:`Deep dives <deep-dives/index>`
        Detailed explorations of particularly complex subsystems such as the solver,
        activation, context, and logging.

Extending conda :octicon:`plug;1em;sd-text-primary`
....................................................

Build on top of conda using its plugin system or consult the formal specifications.

.. glossary::

    :doc:`Plugins <plugins/index>`
        Learn how to extend and customize conda's behavior using the plugin system,
        including hooks for solvers, subcommands, auth handlers, and more.

    :doc:`Specifications <specs/index>`
        Formal specifications for conda internals, including solver state and other
        components.

Contributing & quality :octicon:`heart;1em;sd-text-primary`
............................................................

Guides for writing tests, managing deprecations, and cutting releases.

.. glossary::

    :doc:`Writing tests <writing-tests/index>`
        Guidelines and guides for writing unit and integration tests, using the HTTP
        test server, and testing on Windows with AppLocker.

    :doc:`Deprecations <deprecations>`
        Learn the conda deprecation policy and how to mark APIs and behaviors as
        pending deprecated, deprecated, or removed.

    :doc:`Releasing <releasing>`
        Step-by-step instructions for preparing and publishing a new conda release,
        including the CalVer versioning scheme.

    :doc:`Type hinting <typing>`
        Guidelines for adding and improving type annotations in the conda codebase,
        including custom types and local tooling.

API reference :octicon:`code;1em;sd-text-primary`
..................................................

.. glossary::

    :doc:`API reference </dev-guide/api>`
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
   previews
   specs/index
   typing
