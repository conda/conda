===============
Output Handlers
===============

Output handlers allow plugin authors to customize where output from reporter handlers
is sent. By default, conda supports the ability to send output to standard out, but
output handlers can also be written to support sending output to files or network  streams.

To configure an output handler, it must be specified in the configuration file under the
``reporters`` setting. At a minimum, the output handler must also be associated with one reporter
handler.

The following shows the default configuration for the ``console`` reporter that writes
to ``stdout``:

.. code-block:: yaml

   reporters:
     - backend: console
       output: stdout


.. autoapiclass:: conda.plugins.types.CondaOutputHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_output_handlers

.. _requests.auth.AuthBase: https://docs.python-requests.org/en/latest/api/#requests.auth.AuthBase
.. _Custom Authentication: https://docs.python-requests.org/en/latest/user/advanced/#custom-authentication
