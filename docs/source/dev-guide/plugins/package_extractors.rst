===================
Package extractors
===================

Package extractors handle the unpacking of different package archive formats.
Each extractor specifies which file extensions it supports (e.g., ``.conda``,
``.tar.bz2``) and provides an extraction function.

This plugin hook allows adding support for new package formats without
modifying conda's core code.

.. autoapiclass:: conda.plugins.types.CondaPackageExtractor
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_package_extractors
