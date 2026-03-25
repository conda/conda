======================
``PrefixData`` loaders
======================

The ``PrefixData`` class exposes the contents of a given conda environment
(prefix) as a series of ``PrefixRecord`` objects. This plugin hook allows
users to write logic to expose non-conda packages as conda-like metadata.
This can be useful to allow ``conda list`` to report additional ecosystems,
like PyPI or others.

.. autoapiclass:: conda.plugins.types.CondaPrefixDataLoader
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_prefix_data_loaders
