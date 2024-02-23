========
Settings
========

The settings plugin hook allows plugin authors to add new settings to conda.
Users will be able to use these new parameters either in ``.condarc`` files
or define them as environment variables. For more information on configuration
in conda, see :doc:`Configuration <user-guide/configuration>`.

The plugin hooks relies on using the various :class:`conda.common.configuration.Parameter`
sub-classes (e.g. :class:`conda.common.configuration.PrimitiveParameter` or
:class:`conda.common.configuration.SequenceParameter`) For more examples of how these parameter
classes are used, please see the :class:`conda.base.context.Context` class.

.. autoapiclass:: conda.plugins.types.CondaSetting
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_settings
