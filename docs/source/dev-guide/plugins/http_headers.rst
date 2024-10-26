============
HTTP Headers
============

The HTTP headers plugin hook allows plugin authors to add custom HTTP
headers to HTTP requests within conda. This works by attaching these headers to
our internal :class:`~conda.gateways.connection.session.CondaSession` class.

When defining these headers via the :class:`~conda.plugins.CondaHttpHeader` class,
you can optionally define a ``header_hosts`` parameter. This is a set of strings
representing the different hostnames for which you want the custom headers to be submitted
to. When this is not defined, the custom HTTP headers will be submitted for all hostnames.

.. autoapiclass:: conda.plugins.types.CondaHttpHeader
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_http_headers
