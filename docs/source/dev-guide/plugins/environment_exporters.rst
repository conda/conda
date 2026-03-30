======================
Environment Exporters
======================

The environment exporter plugin hook allows you to create custom export formats for conda environments.
This feature was introduced to enhance the :ref:`conda export <\`\`conda export\`\`>` command with a plugin-based architecture
for extending conda's environment export capabilities.

Overview
========

Environment exporters transform conda environments into various file formats that can be shared,
stored, or used to recreate environments. The plugin system supports both structured formats
(like YAML/JSON) and text-based formats (like explicit URLs or requirement specs).

Built-in exporters include:

* **environment-yaml** - YAML format for cross-platform environments
* **environment-json** - JSON format for programmatic processing
* **explicit** - `CEP 23 <https://conda.org/learn/ceps/cep-0023>`_ compliant explicit URLs format
* **requirements** - :class:`~conda.models.match_spec.MatchSpec` -based requirements format

Plugin Architecture
===================

Environment exporters are registered through the ``conda_environment_exporters`` plugin hook.
Each exporter defines:

* A unique name and optional aliases
* Supported filename patterns for auto-detection
* An export function that transforms environments to the target format

.. autoapiclass:: conda.plugins.types.CondaEnvironmentExporter
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_environment_exporters

Creating an Environment Exporter Plugin
========================================

What follows are several examples showing how to create new export formats using the environment exporters plugin hook.
Please check out our :ref:`Quick start <Quick start>` guide for more detailed instructions on how to
create a conda plugin.

Basic Plugin Structure
-----------------------

Here's a minimal example of an environment exporter plugin:

.. code-block:: python

    import conda.plugins
    from conda.models.environment import Environment


    def export_simple_text(environment: Environment) -> str:
        """Export environment as a simple text list."""
        return "\n".join(
            (
                f"# Environment: {environment.name or environment.prefix}",
                f"# Platform: {environment.platform}",
                f"# Packages:",
                *(str(package) for package in environment.explicit_packages),
            )
        )


    def export_multiplatform_text(environments: Iterable[Environment]) -> str:
        """Export environments as a simple text list."""
        return "\n".join(
            (
                f"# Environment: {environment.name or environment.prefix}",
                f"# Platforms: {', '.join((environment.platform for environment in environments))}",
                f"# Packages:",
                *(
                    str(package)
                    for environment in environments
                    for package in environment.explicit_packages
                ),
            )
        )


    @conda.plugins.hookimpl
    def conda_environment_exporters():
        yield conda.plugins.types.CondaEnvironmentExporter(
            name="simple-text",
            aliases=("simple", "txt-simple"),
            default_filenames=("environment.txt",),
            export=export_simple_text,
        )
        yield conda.plugins.types.CondaEnvironmentExporter(
            name="multiplatform-text",
            aliases=("multiplatform", "txt-multiplatform"),
            default_filenames=("environment.txt",),
            export=export_multiplatform_text,
        )


.. seealso::

   For a general introduction and examples of how to distribute conda plugins,
   see the :doc:`../plugins` quick start guide.

Plugin Components
-----------------

Below, we explain how to use the plugin you've created above with `conda export`.

Name and Aliases
~~~~~~~~~~~~~~~~

The ``name`` field defines the canonical format name used with ``--format``:

.. code-block:: bash

   conda export --format=simple-text

The ``aliases`` tuple provides alternative names for convenience:

.. code-block:: bash

   conda export --format=simple
   conda export --format=txt-simple

.. note::
   Aliases are automatically normalized to lowercase and stripped of whitespace.
   The plugin system will detect and prevent name collisions.

Default Filenames
~~~~~~~~~~~~~~~~~

The ``default_filenames`` tuple specifies filename patterns for automatic format detection:

.. code-block:: bash

   # These would auto-detect the simple-text format
   conda export --file=environment.txt

Export/Multiplatform Export Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are two export functions, one for single platform formats and one for multiplatform formats. Both return a string representation:

* ``export``: receives a single :class:`~conda.models.environment.Environment` object
* ``multiplatform_export``: receives a list of :class:`~conda.models.environment.Environment` objects

Advanced Example: JSON Exporter
-------------------------------

Here's a more sophisticated example that creates a custom JSON format:

.. code-block:: python

    import json
    from typing import Any, Dict

    import conda.plugins.types
    from conda.models.environment import Environment


    def export_custom_json(environment: Environment) -> str:
        """Export environment as custom JSON format."""
        data: Dict[str, Any] = {
            "format_version": "1.0",
            "environment": {
                "name": environment.name,
                "channels": [str(channel) for channel in environment.channels],
            },
        }

        # Add requested_packages as MatchSpec strings
        if environment.requested_packages:
            data["environment"]["requested_packages"] = [
                str(dep) for dep in environment.requested_packages
            ]

        # Add explicit packages with full metadata
        if environment.explicit_packages:
            data["environment"]["explicit_packages"] = [
                {
                    "name": pkg.name,
                    "version": pkg.version,
                    "build": pkg.build,
                    "channel": str(pkg.channel),
                    "url": pkg.url,
                    "md5": pkg.md5,
                }
                for pkg in environment.explicit_packages
            ]

        # Add environment variables
        if environment.variables:
            data["environment"]["variables"] = dict(environment.variables)

        return json.dumps(data, indent=2, sort_keys=True)


    @conda.plugins.hookimpl
    def conda_environment_exporters():
        yield conda.plugins.types.CondaEnvironmentExporter(
            name="custom-json",
            aliases=("cjson",),
            default_filenames=("environment.cjson", "env.cjson"),
            export=export_custom_json,
        )

Error Handling
--------------

Your export function should handle error cases appropriately:

.. code-block:: python

    from conda.exceptions import CondaValueError


    def export_strict_format(environment: Environment) -> str:
        """Export that requires specific conditions."""
        if not environment.requested_packages:
            raise CondaValueError(
                "Cannot export strict format: no requested packages found. "
                "This format requires at least one requested package."
            )

        if not environment.name:
            raise CondaValueError(
                "Cannot export strict format: environment name is required."
            )

        # Continue with export...
        return formatted_content

Working with Different Package Types
=====================================

Understanding Package Collections
---------------------------------

The Environment model provides different package collections for different use cases:

``requested_packages`` (:class:`~conda.models.match_spec.MatchSpec` objects)
  Represents user-requested packages. These are the packages the user explicitly
  asked for, either from history (when using ``--from-history``) or converted
  from installed packages.

``explicit_packages`` (:class:`~conda.models.records.PackageRecord` objects)
  Represents all installed packages with full metadata including URLs, checksums,
  and build information. Used for exact reproduction.

``external_packages`` (dict of str -> list[str])
  Represents external packages. These are packages that are not conda packages.
  For example, pip packages.

Example usage patterns:

.. code-block:: python

    def export_user_requested(environment: Environment) -> str:
        """Export only what the user explicitly requested."""
        if not environment.dependencies:
            raise CondaValueError("No requested packages found")

        lines = []
        for dep in environment.dependencies:
            lines.append(str(dep))  # e.g., "numpy=1.21.0"
        return "\n".join(lines)


    def export_exact_reproduction(environment: Environment) -> str:
        """Export for exact environment reproduction."""
        if not environment.explicit_packages:
            raise CondaValueError("No installed packages found")

        lines = ["@EXPLICIT"]
        for pkg in environment.explicit_packages:
            lines.append(pkg.url)  # Full package URL
        return "\n".join(lines)





Plugin Detection and Conflicts
==============================

Automatic Format Detection
---------------------------

When users run ``conda export --file=filename.ext``, conda:

1. Checks all registered exporters for matching ``default_filenames``
2. If exactly one match is found, uses that exporter
3. If no matches or multiple matches, raises an appropriate error

The detection system is case-insensitive and supports glob-like patterns.

Collision Prevention
--------------------

The plugin system automatically prevents naming conflicts:

* Format names and aliases are normalized (lowercase, stripped)
* Duplicate format names or aliases raise :class:`~conda.exceptions.PluginError`
* This ensures deterministic behavior and clear error messages

Testing Your Plugin
===================

Here's a basic test structure for your exporter plugin:

.. code-block:: python

    import pytest
    from conda.models.environment import Environment
    from conda.testing.fixtures import tmp_env
    from my_export_plugin.exporters import export_custom_json


    def test_custom_json_exporter(tmp_env):
        """Test the custom JSON exporter."""
        environment = Environment.from_prefix(tmp_env.prefix)
        result = export_custom_json(environment)

        # Verify the output format
        import json

        data = json.loads(result)
        assert data["format_version"] == "1.0"
        assert "environment" in data
        assert "name" in data["environment"]


    def test_empty_environment_handling(tmp_env):
        """Test exporter with empty environment."""
        environment = Environment(name="test-empty")

        # Should handle gracefully or raise appropriate error
        result = export_custom_json(environment)
        data = json.loads(result)
        assert data["environment"]["name"] == "test-empty"

Best Practices
==============

1. **Validation**: Always validate inputs and provide clear error messages
2. **Documentation**: Include format specifications and examples in your plugin
3. **Backwards compatibility**: Consider versioning your format for future changes
4. **Performance**: Optimize for large environments with many packages
5. **Cross-platform**: Consider platform differences in your format design

Example Use Cases
=================

Some ideas for custom environment exporters:

* **Docker integration**: Export as Dockerfile or Docker Compose
* **Language-specific**: Export as language package files (package.json, Gemfile, etc.)
* **Cloud deployment**: Export as cloud infrastructure templates
* **Version control**: Export in formats optimized for VCS tracking
* **Documentation**: Export as formatted documentation or reports

Further Reading
===============

For more information about conda plugin development:

- :doc:`Plugin overview <index>` - General plugin development guide
- :doc:`Environment specifiers <environment_specifiers>` - Input counterpart to exporters
- :class:`conda.models.environment.Environment` - Environment model API
- :doc:`conda export <../../commands/export>` - Export command documentation
