``conda plugins``
*****************

Inspect plugins loaded by the running conda installation and manage conda plugin
packages in a selected environment. See :doc:`Plugins
<../user-guide/concepts/conda-plugins>` for installation, update, and removal
examples and guidance on choosing the environment that runs your plugins.

.. versionadded:: 26.11.0

   The ``install``, ``remove``, and ``update`` subcommands.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: plugins
   :nodefault:
   :nodefaultconst:
