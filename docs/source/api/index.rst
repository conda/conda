================
Conda Python API
================

As of conda 4.4, conda can be installed in any environment, not just environments with names starting with _ (underscore). That change was made, in part, so that conda can be used as a Python library.

There are 3 supported public modules. We support:

#. import conda.cli.python_api
#. import conda.api
#. import conda.exports

The first 2 should have very long-term stability. The third is guaranteed to be stable throughout the lifetime of a feature release series--i.e. minor version number.

As of conda 4.5, we do not support ``pip install conda``. However, we are considering that as a supported bootstrap method in the future.


.. toctree::
   :maxdepth: 1
   :caption: Contents

   solver
   python_api
   api
