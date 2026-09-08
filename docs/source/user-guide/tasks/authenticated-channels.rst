============================
Using authenticated channels
============================

Some conda channels require authentication before packages can be
downloaded. For example, a private channel may require an access token,
or a company-hosted channel may require HTTP basic authentication.

Conda supports authenticated channels through authentication handler
plugins. For common authenticated-channel workflows, use the
`conda-auth <https://conda-incubator.github.io/conda-auth/>`_ plugin.

Install conda-auth
==================

Install ``conda-auth`` into your base environment:

.. code-block:: shell

   conda self install conda-auth

Because ``conda-auth`` is a conda plugin, it must be installed in the
environment where conda itself is installed, usually ``base``.

Log in with HTTP basic authentication
=====================================

Use HTTP basic authentication for channels that require a username and
password:

.. code-block:: shell

   conda auth login https://example.com/my-protected-channel --basic

The command prompts for your credentials. After you log in, use the
channel as you normally would:

.. code-block:: shell

   conda install --channel https://example.com/my-protected-channel package-name

Log in with token authentication
================================

Use token authentication for channels that require an access token:

.. code-block:: shell

   conda auth login my-private-channel --token

When you provide a bare channel name such as ``my-private-channel``,
``conda-auth`` uses the corresponding channel on ``anaconda.org`` by default.

The command prompts for your token. After you log in, use the channel as
you normally would:

.. code-block:: shell

   conda install --channel my-private-channel package-name

Log out of an authenticated channel
===================================

To remove stored credentials for a channel, log out:

.. code-block:: shell

   conda auth logout https://example.com/my-protected-channel

Security notes
==============

The ``conda auth login`` command prompts for secrets by default. This is
recommended for interactive use because it avoids placing passwords or
tokens directly in your shell history.

Passing passwords or tokens directly on the command line may be useful
for non-interactive automation, but it can expose secrets in shell
history, process listings, or CI logs. Follow your organization's secret
management practices when using authenticated channels in automation.

Advanced authentication configuration
=====================================

The ``channel_settings`` configuration option can associate a channel
with a specific authentication handler. This is mainly useful for
advanced workflows or custom authentication plugins.

For more information, see the
`conda-auth Getting Started guide
<https://conda-incubator.github.io/conda-auth/user/index.html#getting-started>`_,
:ref:`channel_settings <channel-settings>`, and the developer documentation
for :doc:`/dev-guide/plugins/auth_handlers`.
