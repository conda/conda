=============
Auth Handlers
=============

The auth handlers plugin hook allows plugin authors to enable new modes
of authentication within conda. Registered auth handlers will be
available to configure on a per channel basis via the ``channel_settings``
configuration option in the ``.condarc`` file.

Auth handlers are subclasses of the `requests.auth.AuthBase`_ class. Please
read the request documentation on `Custom Authentication`_ for more information
on how to use this class.


.. autoapiclass:: conda.plugins.types.CondaAuthHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_auth_handlers

.. _requests.auth.AuthBase: https://docs.python-requests.org/en/latest/api/#requests.auth.AuthBase
.. _Custom Authentication: https://docs.python-requests.org/en/latest/user/advanced/#custom-authentication
