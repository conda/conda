"""
Cached repodata with `.jlap` incremental diffs, implemented as a ConnectionAdapter.
"""

# The least invasive, but not necessarily best, place to add cache.

INTERCEPT_PATHS = ["https://conda.anaconda.org/conda-forge/", "https://repo.anaconda.com/pkgs/"]

import logging

log = logging.getLogger(__name__)

try:
    from . import repodata_proxy, sync_jlap
    from ... import BaseAdapter

    class JlapAdapter(BaseAdapter):
        def __init__(self, base_adapter):
            self.base_adapter = base_adapter

        def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
            """Sends PreparedRequest object. Returns Response object.

            :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
            :param stream: (optional) Whether to stream the request content.
            :param timeout: (optional) How long to wait for the server to send
                data before giving up, as a float, or a :ref:`(connect timeout,
                read timeout) <timeouts>` tuple.
            :type timeout: float or tuple
            :param verify: (optional) Either a boolean, in which case it controls whether we verify
                the server's TLS certificate, or a string, in which case it must be a path
                to a CA bundle to use
            :param cert: (optional) Any user-provided SSL certificate to be trusted.
            :param proxies: (optional) The proxies dictionary to apply to the request.
            """
            if not repodata_proxy.supported.match(request.url):
                log.debug("Skip intercept %s", request.url)
                return self.base_adapter.send(request, stream, timeout, verify, cert, proxies)

            log.debug("Intercept %s", request.url)
            return repodata_proxy.send(request, self.base_adapter)

    if True:
        log.setLevel(logging.DEBUG)
        repodata_proxy.log.setLevel(logging.DEBUG)
        sync_jlap.log.setLevel(logging.DEBUG)

except ImportError as e:
    repodata_proxy = None


# Called several times. Would conda perform better with a persistent Session()?
# (may be in separate threads)
def attach(session, base_adapter):
    """
    Mount adapter to session, intercepting supported URLs.

    base_adapter: normal https:// adapter
    """
    if repodata_proxy is None:
        print("no jlap cache; requires repodata_proxy, jsonpatch, ...")
        return

    print("install jlap cache")
    interceptor = JlapAdapter(base_adapter)

    for path in INTERCEPT_PATHS:
        session.mount(path, interceptor)

    return session
