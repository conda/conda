===============
Request Headers
===============

The request headers plugin hooks allows plugin authors to add custom HTTP
headers to HTTP requests within conda. This works by inserting these headers while preparing
the :class:`requests.models.PreparedRequest` object when calling :func:`requests.sessions.Session.request`.

There are two hooks available for this purpose:
1. :func:`~conda.plugins.hookspecs.CondaSpecs.conda_session_headers`: This hook is used to define
   the custom headers that will be submitted with all HTTP requests (or a subset of hosts)
2. :func:`~conda.plugins.hookspecs.CondaSpecs.conda_request_headers`: This hook is used to define
   the custom headers that will be submitted with a specific HTTP request.

.. warning::

   While the second hook (:func:`~conda.plugins.hookspecs.CondaSpecs.conda_request_headers`)
   can also create session headers, it is recommended to use the first hook
   (:func:`~conda.plugins.hookspecs.CondaSpecs.conda_session_headers`) for improved caching performance.

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_request_headers

Both hook use the :class:`~conda.plugins.CondaRequestHeader` class to define headers:

.. autoapiclass:: conda.plugins.types.CondaRequestHeader
   :members:
   :undoc-members:
