.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. =====
.. Conda
.. =====

.. figure::  images/conda_logo.svg
   :align:   center

.. raw:: html

  <!-- Begin MailChimp Signup Form -->
   <link href="//cdn-images.mailchimp.com/embedcode/classic-10_7.css" rel="stylesheet" type="text/css">
   <style type="text/css">
   	#mc_embed_signup{background:#fff; clear:left; font:14px Helvetica,Arial,sans-serif; }
   	/* Add your own MailChimp form style overrides in your site stylesheet or in this style block.
   	   We recommend moving this block and the preceding CSS link to the HEAD of your HTML file. */
   </style>
   <div id="mc_embed_signup">
   <form action="//pydata.us13.list-manage.com/subscribe/post?u=28f85eefa68de727efcbd93f9&amp;id=cb4ca49e7d" method="post" id="mc-embedded-subscribe-form" name="mc-embedded-subscribe-form" class="validate" target="_blank" novalidate>
       <div id="mc_embed_signup_scroll">
   	<h1>Conda Announcements</h1>
    <div><p style="font-size:1.3em;font-weight:700;">News and updates directly from the Conda core team.</p></div>
    <div style="font-size:1em; color:#777777; font-weight:500;">Privacy Policy: We will never sell, give away, or further distribute your email address to third parties.</div>
   <div class="indicates-required"><span class="asterisk">*</span> indicates required</div>
   <div class="mc-field-group">
   	<label for="mce-EMAIL">Email Address  <span class="asterisk">*</span>
   </label>
   	<input type="email" value="" name="EMAIL" class="required email" id="mce-EMAIL">
   </div>
   <div class="mc-field-group">
   	<label for="mce-NAME">Name </label>
   	<input type="text" value="" name="NAME" class="" id="mce-NAME">
   </div>
   <div class="mc-field-group">
   	<label for="mce-AFFILIATIO">Affiliations (e.g. Company, Projects) </label>
   	<input type="text" value="" name="AFFILIATIO" class="" id="mce-AFFILIATIO">
   </div>
   <p><a href="http://us13.campaign-archive1.com/home/?u=28f85eefa68de727efcbd93f9&id=cb4ca49e7d" title="View previous announcements.">View previous announcements.</a></p>
   	<div id="mce-responses" class="clear">
   		<div class="response" id="mce-error-response" style="display:none"></div>
   		<div class="response" id="mce-success-response" style="display:none"></div>
   	</div>    <!-- real people should not fill this in and expect good things - do not remove this or risk form bot signups-->
       <div style="position: absolute; left: -5000px;" aria-hidden="true"><input type="text" name="b_28f85eefa68de727efcbd93f9_cb4ca49e7d" tabindex="-1" value=""></div>
       <div class="clear"><input type="submit" value="Subscribe" name="subscribe" id="mc-embedded-subscribe" class="button"></div>
       </div>
   </form>
   </div>
   <script type='text/javascript' src='//s3.amazonaws.com/downloads.mailchimp.com/js/mc-validate.js'></script><script type='text/javascript'>(function($) {window.fnames = new Array(); window.ftypes = new Array();fnames[0]='EMAIL';ftypes[0]='email';fnames[1]='NAME';ftypes[1]='text';fnames[2]='AFFILIATIO';ftypes[2]='text';}(jQuery));var $mcj = jQuery.noConflict(true);</script>
   <!--End mc_embed_signup-->


Conda is an open source package management system and environment management system for installing multiple
versions of software packages and their dependencies and switching easily between them. It works on
Linux, OS X and Windows, and was created for Python programs but can package and distribute any software.

Conda is included in Anaconda and Miniconda. Conda is also included in the Continuum `subscriptions <https://www.continuum.io/anaconda-subscriptions>`_
of Anaconda, which provide on-site enterprise package and environment management for Python, R, Node.js, Java, and other application
stacks. Conda is also available on pypi, although that approach may not be as up-to-date.

* Miniconda is a small "bootstrap" version that includes only conda, Python, and the packages they depend on. Over 720
  scientific packages and their dependencies can be installed individually from the Continuum repository with
  the "conda install" command.

* Anaconda includes conda, conda-build, Python, and over 150 automatically installed scientific packages and
  their dependencies. As with Miniconda, over 250 additional scientific packages can be installed individually with
  the "conda install" command.

* pip install conda uses the released version on pypi.  This version allows you to create new conda environments using
  any python installation, and a new version of Python will then be installed into those environments.  These environments
  are still considered "Anaconda installations."

The `conda` command is the primary interface for managing `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations. It can query
and search the Anaconda package index and current Anaconda installation,
create new conda environments, and install and update packages into existing
conda environments.



.. toctree::
   :hidden:

   get-started
   using/index
   building/build
   help/help
   get-involved

Presentations & Blog Posts
--------------------------

`Packaging and Deployment with conda - Travis Oliphant <https://speakerdeck.com/teoliphant/packaging-and-deployment-with-conda>`_

`Python 3 support in Anaconda - Ilan Schnell <https://www.continuum.io/content/python-3-support-anaconda>`_

`New Advances in conda - Ilan Schnell <https://www.continuum.io/blog/developer/new-advances-conda>`_

`Python Packages and Environments with conda - Bryan Van de Ven <https://www.continuum.io/content/python-packages-and-environments-conda>`_

`Advanced features of Conda, part 1 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-1>`_

`Advanced features of Conda, part 2 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-2>`_

Requirements
------------

* python 2.7, 3.4, or 3.5
* pycosat
* pyyaml
* requests

What's new in conda 4.1?
------------------------

This release contains many small bug fixes for all operating systems, and a few 
special fixes for Windows behavior. The 
`changelog <https://github.com/conda/conda/releases/tag/4.1.0>`_ contains a 
complete list of changes. 

**Notable changes for all systems Windows, OS X and Linux:**

* **Channel order now matters.** The most significant conda change is that 
  when you add channels, channel order matters. If you have a list of channels 
  in a .condarc file, conda installs the package from the first channel where 
  it's available, even if it's available in a later channel with a higher 
  version number.
* **No version downgrades.** Conda remove no longer performs version 
  downgrades on any remaining packages that might be suggested to resolve 
  dependency losses; the package will just be removed instead.
* **New YAML parser/emitter.** PyYAML is replaced with ruamel.yaml, 
  which gives more robust control over yaml document use. 
  `More on ruamel.yaml <http://yaml.readthedocs.io/en/latest/>`_
* **Shebang lines over 127 characters are now truncated (Linux, OS X 
  only).** `Shebangs <https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ are
  the first line of the many executable scripts that tell the operating 
  system how to execute the program.  They start with ``#!``. Most OSes
  don't support these lines over 127 characters, so conda now checks 
  the length and replaces the full interpreter path in long lines with 
  ``/usr/bin/env``. When you're working in a conda environment that
  is deeply under many directories, or you otherwise have long paths
  to your conda environment, make sure you activate that environment
  now.
* **Changes to conda list command.** When looking for packages that 
  aren’t installed with conda, conda list now examines the Python 
  site-packages directory rather than relying on pip.
* **Changes to conda remove command.** The command  ``conda remove --all`` 
  now removes a conda environment without fetching information from a remote 
  server on the packages in the environment.
* **Conda update can be turned off and on.** When turned off, conda will 
  not update itself unless the user manually issues a conda update command. 
  Previously conda updated any time a user updated or installed a package 
  in the root environment. Use the option ``conda config set auto_update_conda false``.
* **Improved support for BeeGFS.** BeeGFS is a parallel cluster file 
  system for performance and designed for easy installation and 
  management. `More on BeeGFS <http://www.beegfs.com/content/documentation/>`_

**Windows-only changes include:**

* **Shortcuts are no longer installed by default on Windows.** Shortcuts can 
  now be installed with the ``--shortcuts`` option. Example 1: Install a shortcut 
  to Spyder with ``conda install spyder --shortcut``. Note if you have Anaconda 
  (not Miniconda), you already have this shortcut and Spyder. Example 2: 
  Install the open source package named ``console_shortcut``. When you click 
  the shortcut icon, a terminal window will open with the environment 
  containing the ``console_shortcut`` package already activated. ``conda install 
  console_shortcut --shortcuts``
* **Skip binary replacement on Windows.** Linux & OS X have binaries that 
  are coded with library locations, and this information must sometimes be 
  replaced for relocatability, but Windows does not generally embed prefixes 
  in binaries, and was already relocatable. We skip binary replacement on 
  Windows.



See the `changelog <https://github.com/conda/conda/releases/tag/4.1.0>`_ for 
a complete list of changes. 
