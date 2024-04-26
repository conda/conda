===============
Output Handlers
===============

Output handlers allow plugin authors to customize where output from reporter handlers
is sent. By default, conda supports the ability to send output to standard out, but
output handlers can also be written to support sending output to files or network  streams.

To configure a output handler, they must be specified in the configuration file under the
reporters setting. At a minimum, the output handler must also be associated with one reporter
handler.

An example of a setting a file output handler using the default ``console`` reporter handler
is shown below:

.. code-block:: yaml

   reporters:
     - backend: console
       output: file


.. autoapiclass:: conda.plugins.types.CondaOutputHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_output_handlers

.. _requests.auth.AuthBase: https://docs.python-requests.org/en/latest/api/#requests.auth.AuthBase
.. _Custom Authentication: https://docs.python-requests.org/en/latest/user/advanced/#custom-authentication
