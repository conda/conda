``conda env export``
********************

.. note::
   A newer ``conda export`` command is now available with enhanced functionality, including
   multiple export formats and a plugin-based architecture. See :doc:`conda export <../export>`
   for the modern approach to environment export.

.. argparse::
   :module: conda.cli.conda_argparse
   :func: generate_parser
   :prog: conda
   :path: env export
   :nodefault:
   :nodefaultconst:

Overview
========

The ``conda env export`` command exports conda environments to YAML format.
This command continues to be fully supported.

For new projects, consider :doc:`conda export <../export>`, which provides additional features:

* Multiple export formats (YAML, JSON, explicit, requirements)
* Automatic format detection based on filename
* Plugin-based architecture for custom formats
* Enhanced cross-platform compatibility options

Alternative: Enhanced Export Command
====================================

If you're interested in additional export formats and functionality,
the ``conda export`` command offers enhanced capabilities:

**Traditional (conda env export):**

.. code-block:: bash

   conda env export > environment.yml
   conda env export --from-history > environment.yml

**Enhanced (conda export):**

.. code-block:: bash

   conda export --format=environment-yaml > environment.yaml
   conda export --from-history --format=environment-yaml > environment.yaml

The enhanced command provides additional features:

.. code-block:: bash

   # Auto-detect format from filename
   conda export --file=environment.yaml

   # Export to different formats
   conda export --format=environment-json --file=environment.json
   conda export --format=explicit --file=explicit.txt

See Also
========

- :doc:`conda export <../export>` - Enhanced environment export command with multiple formats
- :doc:`Managing environments <../../user-guide/tasks/manage-environments>` - Environment management guide
