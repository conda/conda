---------------------------------
Create Python 2 or 3 environments
---------------------------------

Anaconda supports Python 2.6, 2.7, 3.3, and 3.4.  The default is Python 2.7 or
3.4, depending on which installer you used.

To get started, you need to create an environment using the :ref:`conda create <create_example>`
command.

.. code-block:: bash

    $ conda create -n py34 python=3.4 anaconda

Here, 'py34' is the name of the environment to create, and 'anaconda' is the
meta-package that includes all of the actual Python packages comprising
the Anaconda distribution.  When creating a new environment and installing
the Anaconda meta-package, the NumPy and Python versions can be specified,
e.g. `numpy=1.7` or `python=3.4`.

.. code-block:: bash

    $ conda create -n py26 python=2.6 anaconda

After the environment creation process completes, adjust your **PATH** variable
to point to this directory.  On Linux/MacOSX systems, this can be easily
done using:

.. code-block:: bash

    $ source activate <env name>

    # This command assumes ~/anaconda/bin/activate is the first 'activate' on your current PATH

This will modify your Bash PS1 to include the name of the environment.

.. code-block:: bash

   $ source activate myenv
   (myenv)$

You can disable this with ``conda config --set changeps1 no``. The environment
variable ``CONDA_DEFAULT_ENV`` is set to the currently activated environment.

On Windows systems, use ``activate`` instead of ``source activate``.

Now you're ready to begin using the Python located in your created
environment.

If you would like to deactivate this environment and revert your **PATH** to
its previous state, use:

.. code-block:: bash

    $ source deactivate

On Windows, this is just ``deactivate``.
