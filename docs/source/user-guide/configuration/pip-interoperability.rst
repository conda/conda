===================================
Improving interoperability with pip
===================================

The conda 4.6.0 release added improved support for interoperability between conda and pip.
This feature is still experimental and is therefore off by default.

With this interoperability,
conda can use pip-installed packages to satisfy dependencies,
cleanly remove pip-installed software, and replace them with
conda packages when appropriate.

If you’d like to try the feature, you can set this ``.condarc`` setting::

   conda config --set pip_interop_enabled True

.. note::

   Setting ``pip_interop_enabled`` to ``True`` may slow down conda.

Even without activating this feature, conda now understands pip metadata
more intelligently. For example, if we create an environment with conda::

   conda create -y -n some_pip_test python=3.7 imagesize=1.0

Then we update imagesize in that environment using pip::

   conda activate some_pip_test
   pip install -U imagesize

Prior to conda 4.6.0, the ``conda list`` command returned ambiguous results::

   imagesize                 1.1.0

   imagesize                 1.0.0 py37_0

Conda 4.6.0 now shows only one entry for imagesize (the newer pip entry)::

   imagesize                 1.1.0 pypi_0    pypi
