
.. _config:

-------------
Configuration
-------------

There is very little user configuration that conda requires; however, conda
will read minimal configuration from a ``$HOME/.condarc`` file, if it is
present. The ``.condarc`` file follows simple ``YAML syntax``.

The condarc file can be used to affect

- Channels - Where conda looks for packages

- Proxy Settings - Configure to use conda behind a proxy server

- Environment Directories - Where conda lists known environments

- Bash prompt - Whether to update the bash prompt with the current activated environment name

- Binstar Upload - Whether user-built packages should be uploaded to Binstar.org

- Environment defaults - Default packages or features to include in new environments

Here is an example:

.. include:: ../../condarc
   :code: yaml

You can use the ``conda config`` command to modify configuration options in
``.condarc`` from the command line.

--------------
Tab Completion
--------------
