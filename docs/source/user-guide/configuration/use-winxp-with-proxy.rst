=================================================
Using conda on Windows XP with or without a proxy
=================================================

Although Windows XP mainstream support and Extended Support from
Microsoft have ended, and Windows XP is no longer one of the
target systems supported by Anaconda, some users have had success
using Anaconda on Windows XP with the methods described on this
page.

Anaconda 2.3.0 is the last version of Python 3-based Anaconda
to support Windows XP. Anaconda 2.4 and later have a version of
Python 3 built with Visual Studio 2015, which by default does not
support Windows XP.

You can install Anaconda 2.3.0 and then update it with
``conda update conda`` and ``conda update --all``. Download
``Anaconda3-2.3.0-Windows-x86.exe`` at
https://repo.anaconda.com/archive/. Install it in any location,
such as ``C:\Anaconda``.

Using a proxy with Windows XP
=============================

To configure conda for use behind a corporate proxy that uses
proxy auto-config (PAC) files and SSL certificates for secure
connections:

#. Find a proxy server address from the PAC file:

   #. Open Internet Explorer.

   #. From the **Tools** menu, select Internet Options, and then
      click the **Connections** tab.

   #. On the **Connections** tab, click the LAN Settings button.

   #. In the LAN Settings dialog box, copy the address under
      the Use automatic configuration script checkbox.

   #. Click the Cancel button to close the LAN settings.

   #. Click the Cancel button to close the Internet Options.

   #. Paste the address into the Internet Explorer address bar,
      then press the Enter key.

   #. In the PAC file that opens, search for ``return`` until you
      find what looks like a proxy IP or DNS address with the
      port number, which may take some time in a long file.

   #. Copy the address and port number.

#. Follow the :ref:`.condarc instructions <config-overview>`
   to create a file named ``.condarc`` in your home directory or
   the installation directory, such as ``C:\Anaconda\.condarc``.

#. Follow the :ref:`.condarc proxy server instructions
   <config-proxy>` to add proxy information to the ``.condarc``
   file.

If you decide to include any passwords, be aware of
transformations that can affect special characters.

EXAMPLE: This example shows proxy information with passwords::

  proxy_servers:
    http: http://user:pass@corp.com:8080
    https: https://user:pass@corp.com:8080

  ssl_verify: False

If you include proxy information without passwords, you will be
asked to answer authentication prompts at the command line.

EXAMPLE: This example shows proxy information without passwords::

  proxy_servers:
    http: http://corp.com:8080
    https: https://corp.com:8080

  ssl_verify: False

Once the proxy is configured, you can run ``conda update conda``
and then create and manage environments with the `Anaconda
Navigator <https://docs.anaconda.com/anaconda/navigator/>`_.

Some packages such as ``flask-login`` may not be available
through conda, so you may need to use pip to install them:

#. To use pip securely over https::

     pip install --trusted-host pypi.python.org package-name

#. If the secure https proxy fails, you can force pip to use an
   insecure http proxy instead::

     pip install --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org package-name
