=========
API Guide
=========

As of conda 4.4, conda can be installed in any environment, not just environments with names starting with _ (underscore). That change was made, in part, so that conda can be used as a Python library.

As of conda 4.5, we do not support ``pip install conda``. However, we are considering that as a supported bootstrap method in the future.

See :doc:`file-writes` for reading file snapshots and writing bytes with conflict
detection from conda or downstream code.

.. toctree::
   :hidden:
   :maxdepth: 2
   :titlesonly:

   file-writes
   api/conda/index
