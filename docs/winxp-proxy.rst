===================================
Windows XP with proxy configuration
===================================

Although Windows XP mainstream support and Extended Support from Microsoft have ended and Windows XP is no longer one of the target systems supported by Anaconda, some users have had success using Anaconda on Windows XP with the following steps.

The last Python 3-based Anaconda version to support Windows XP is Anaconda 2.3.0. (Anaconda 2.4 and later have a version of Python 3 built with Visual Studio 2015, which by default does not support Windows XP.) It is still possible to install Anaconda 2.3.0 and then update it with ``conda update conda`` and ``conda update --all``. The file to download is ``Anaconda3-2.3.0-Windows-x86.exe`` at https://repo.continuum.io/archive/ , and it can be installed in any location, such as ``C:\Anaconda`` .

When behind a corporate proxy that uses proxy auto-config (PAC) files and SSL certificates for secure connections:

* To find a proxy server address from the PAC file, open "Internet Explorer > Tools > Internet Options > Connections tab > LAN Settings", and copy the address beneath "Use automatic configuration script". Paste this address into Internet Explorer and choose "Open". Search the file for "return" until you find what looks like a proxy IP or DNS address with the port number, which may take some time if the PAC file is long. Copy the address and port number.
* Follow the `.condarc instructions <http://conda.pydata.org/docs/config.html#the-conda-configuration-file-condarc>`_ to create a file named ``.condarc`` in your home directory or the installation directory, such as ``C:\Anaconda\.condarc``.
* Follow the `.condarc proxy server instructions <http://conda.pydata.org/docs/config.html#configure-conda-for-use-behind-a-proxy-server-proxy-servers>`_ and add the proxy information. If you decide to include any passwords in the file, beware of transformations that can affect special characters.

Here is an example of proxy information with passwords::

  proxy_servers:
    http: http://user:pass@corp.com:8080
    https: https://user:pass@corp.com:8080

  ssl_verify: False

You may also save ``.condarc`` without passwords, and answer authentication prompts on the command line instead. Here is an example of proxy information without passwords::

  proxy_servers:
    http: http://corp.com:8080
    https: https://corp.com:8080

  ssl_verify: False

Once the proxy is configured correctly, you may run ``conda update conda`` and then create and manage environments with the Anaconda Launcher GUI.

Some packages such as ``flask-login`` may not be available through conda, so you may need to use pip to install them. This is the normal way to use pip securely over https::

  pip install --trusted-host pypi.python.org package-name

If the secure https proxy fails, it is possible to force pip to use an insecure http proxy instead::

  pip install --index-url=http://pypi.python.org/simple/ --trusted-host pypi.python.org package-name
