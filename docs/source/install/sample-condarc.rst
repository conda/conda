====================
Sample .condarc file
====================

.. code-block:: yaml

  # This is a sample .condarc file. It adds the r Anaconda.org channel and enables
  # the show_channel_urls option.

  # channel locations. These override conda defaults, i.e., conda will
  # search *only* the channels listed here, in the order given. Use "defaults" to
  # automatically include all default channels. Non-url channels will be
  # interpreted as Anaconda.org usernames (this can be changed by modifying the
  # channel_alias key; see below). The default is just 'defaults'.
  channels:
    - r
    - defaults

  # Show channel URLs when displaying what is going to be downloaded and
  # in 'conda list'. The default is False.
  show_channel_urls: True


  # See http://conda.pydata.org/docs/install/config.html for more information about this file.
