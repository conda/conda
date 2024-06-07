================
Reporter Streams
================

Reporter streams allow plugin authors to customize where output from reporter backends
is sent. By default, conda supports the ability to send output to standard out, but
reporter streams can also be written to support sending output to files or network streams.

To configure a reporter stream, it must be specified in the configuration file under the
``reporters`` setting. At a minimum, the reporter stream must also be associated with one
reporter backend.

The following shows the default configuration for the ``console`` reporter that uses the
``stdout`` stream:

.. code-block:: yaml

   reporters:
     - backend: console
       stream: stdout


.. autoapiclass:: conda.plugins.types.CondaReporterStream
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_reporter_streams
