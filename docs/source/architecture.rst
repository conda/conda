Architecture
============

Conda is a complex system of many components and can be hard to
understand for users and developers alike. The following
C4 model based architecture diagrams should help in that regard.

As a refresher, the C4 model tries to visualize complex software
systems at different levels of detail, and explaining the functionality
to different types of audience.

C4 stands for the for levels: Context, Container, Component, Code.

Level 1: System Context
-----------------------

This is the overview, 30,000 feet view on conda, to better understand
how conda in the center of the diagram interacts with other
systems and how users relate to it.

.. uml:: umls/Context.puml
   :width: 80%

Level 2: Container
------------------

This level is zooming in to conda on a system level, which was
in the center of the Level 1 diagram, to show the high-level shape
of the software architecture of and the various responsibilities
in conda, including major technology choices and communication
patterns between the various containers.

Channels
^^^^^^^^

.. uml:: umls/container_channels.puml
   :width: 80%

Conda
^^^^^

.. uml:: umls/container_conda.puml
   :width: 80%

Level 3: Component
------------------

Yet another zoom-in, in which individual containers from Level 2
are decomposed to show major building blocks in conda and their
interactions. Those building blocks are called components in
the sense that they each have a higher function and relate to
an identifiable responsibility and implementation details.

Level 4: Code
-------------

This part is auto-generated based on the current code and shows
how the code is structured and how it interacts. For brevity this
covers only a number of key components of conda, the CLI, solver
and test suite.
