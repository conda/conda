=============
Auth Handlers
=============

The auth handlers plugin hook allows plugin authors to enable new modes
of authentication within conda. Registered auth handlers will be
available to configure on a per channel basis via the ``channel_settings``
configuration option in the ``.condarc`` file.

Auth handlers are subclasses of the :class:`~conda.plugins.types.ChannelAuthBase` class,
which is itself a subclass of `requests.auth.AuthBase`_.
The :class:`~conda.plugins.types.ChannelAuthBase` class adds an additional ``channel_name``
property to the `requests.auth.AuthBase`_ class. This is necessary for appropriate handling of
channel based authentication in conda.

For more information on how to implement your own auth handlers, please read the requests
documentation on `Custom Authentication`_.


.. autoapiclass:: conda.plugins.types.CondaAuthHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_auth_handlers

.. _requests.auth.AuthBase: https://docs.python-requests.org/en/latest/api/#requests.auth.AuthBase
.. _Custom Authentication: https://docs.python-requests.org/en/latest/user/advanced/#custom-authentication
