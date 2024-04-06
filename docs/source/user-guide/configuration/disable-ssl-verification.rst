==========================
Disabling SSL verification
==========================

Using conda with SSL is strongly recommended, but it is possible to disable SSL
and it may be necessary to disable SSL in certain cases.

Some corporate environments use proxy services that use Man-In-The-Middle
(MITM) attacks to sniff encrypted traffic. These services can interfere with
SSL connections such as those used by conda and pip to download packages from
repositories such as PyPI.

If you encounter this interference, you should set up the proxy service's
certificates so that the ``requests`` package used by conda can recognize and
use the certificates.

For cases where this is not possible, conda-build versions 3.0.31 and higher
have an option that disables SSL certificate verification and allows this
traffic to continue.

``conda skeleton pypi`` can disable SSL verification when pulling packages
from a PyPI server over HTTPS.

.. warning::
   This option causes your computer to download and execute arbitrary
   code over a connection that it cannot verify as secure. This is not
   recommended and should only be used if necessary. Use this option at your own
   risk.

To disable SSL verification when using ``conda skeleton pypi``, set the
``SSL_NO_VERIFY`` environment variable to either ``1`` or ``True`` (case
insensitive).

On \*nix systems:

.. code-block:: bash

    SSL_NO_VERIFY=1 conda skeleton pypi a_package

And on Windows systems:

.. code-block:: batch

    set SSL_NO_VERIFY=1
    conda skeleton pypi a_package
    set SSL_NO_VERIFY=

We recommend that you unset this environment variable immediately after use.
If it is not unset, some other tools may recognize it and incorrectly use
unverified SSL connections.

Using this option will cause ``requests`` to emit warnings to STDERR about
insecure settings. If you know that what you're doing is safe, or have been
advised by your IT department that what you're doing is safe, you may ignore
these warnings.
=============================================
Disabling SSL verification via conda settings
=============================================

If the above doesn't work use 

.. code-block:: bash

   conda config --set ssl_verify False
   # Do conda commands
   conda config --set ssl_verify True
