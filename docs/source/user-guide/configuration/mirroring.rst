==================
Mirroring channels
==================

The conda configuration system has several keys that can be used to set up a mirrored context.

The default setup
=================

By default, ``conda`` can serve packages from two main locations:

- ``repo.anaconda.com``: this is where ``defaults`` points to by default.
  This base location is hardcoded in the default value of ``default_channels``:
    - ``https://repo.anaconda.com/pkgs/main``
    - ``https://repo.anaconda.com/pkgs/r``
    - ``https://repo.anaconda.com/pkgs/msys2``
- ``conda.anaconda.org``: this is where conda clients look up community channels like ``conda-forge`` or ``bioconda``.
  This base location can be configured via ``channel_alias``.

So, when it comes to mirroring these channels, you have to account for those two locations.


Mirror ``defaults``
===================

Use ``default_channels`` to overwrite the :doc:`default configuration </configuration>`. For example:

.. code-block:: yaml

    default_channels:
        - https://my-mirror.com/pkgs/main
        - https://my-mirror.com/pkgs/r
        - https://my-mirror.com/pkgs/msys2


Mirror all community channels
=============================

Redefine ``channel_alias`` to point to your mirror. For example:

.. code-block:: yaml

    channel_alias: https://my-mirror.com

This will make ``conda`` look for all community channels at ``https://my-mirror.com/conda-forge``, ``https://my-mirror.com/bioconda``, etc.


Mirror only some community channels
===================================

If you want to mirror only some community channels, you must use ``custom_channels``.
This takes precedence over ``channel_alias``. For example:

.. code-block:: yaml

    custom_channels:
        conda-forge: https://my-mirror.com/conda-forge

With this configuration, conda-forge will be looked up at ``https://my-mirror.com/conda-forge``.
All other community channels will be looked up at ``https://conda.anaconda.org``.


.. note::

    Feel free to explore all the available options in :doc:`/configuration`.
