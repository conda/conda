============
Architecture
============

Conda is a complex system of many components and can be hard to
understand for users and developers alike. The following
`C4 model`_ based architecture diagrams should help in that regard.
As a refresher, the C4 model tries to visualize complex software
systems at different levels of detail, and explaining the functionality
to different types of audience.

.. note::

   These diagrams represent the state of conda at the time
   when the documentation was automatically build as part of the
   development process for conda |version| (|today|).

C4 stands for the for levels:

1. :ref:`Context <context>`
2. :ref:`Container <container>`
3. :ref:`Component <component>`
4. :ref:`Code <code>`

.. _context:

Level 1: Context
----------------

This is the overview, 30,000 feet view on conda, to better understand
how conda in the center of the diagram interacts with other
systems and how users relate to it.

More information about how to interpret this diagram can be found in
the `C4 model`_ documentation about the `System Context diagram`_.

.. uml:: umls/context/context.puml
   :width: 80%

.. _container:

Level 2: Container
------------------

This level is zooming in to conda on a system level, which was
in the center of the Level 1 diagram, to show the high-level shape
of the software architecture of and the various responsibilities
in conda, including major technology choices and communication
patterns between the various containers.

More information about how to interpret the following diagrams can be found
in the `C4 model`_ documentation about the `Container diagram`_.

Channels
^^^^^^^^

The following diagram focuses on the channels container from the level 1
diagram.

.. uml:: umls/container/channels.puml

Conda
^^^^^

The following diagram focuses on the conda container from the level 1 diagram.

.. uml:: umls/container/conda.puml

.. _component:

Level 3: Component
------------------

Yet another zoom-in, in which individual containers from Level 2
are decomposed to show major building blocks in conda and their
interactions. Those building blocks are called components in
the sense that they each have a higher function and relate to
an identifiable responsibility and implementation details.

.. uml:: umls/packages_conda.puml

More information about how to interpret this diagram can be found in
the `C4 model`_ documentation about the `Component diagram`_.

.. _code:

Level 4: Code
-------------

This part is auto-generated based on the current code and shows
how the code is structured and how it interacts. For brevity this
ignores a number of subsystems like the public API and exports modules,
utility and vendor packages.

More information about how to interpret this diagram can be found in
the `C4 model`_ documentation about the `Code diagram`_.

.. uml:: umls/classes_conda.puml

.. _`C4 model`: https://c4model.com/
.. _`System Context diagram`: https://c4model.com/#SystemContextDiagram
.. _`Container diagram`: https://c4model.com/#ContainerDiagram
.. _`Component diagram`: https://c4model.com/#ComponentDiagram
.. _`Code diagram`: https://c4model.com/#CodeDiagram
