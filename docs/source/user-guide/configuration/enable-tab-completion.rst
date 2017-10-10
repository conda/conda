========================
Enabling tab completion
========================

Conda supports tab completion in bash shells via the argcomplete
package.

To enable tab completion:

#. Make sure that argcomplete is installed:

   .. code-block:: bash

      conda install argcomplete

#. Add the following code to your bash profile:

   .. code-block:: bash

      eval "$(register-python-argcomplete conda)"

#. Test it:

   #. Open a new Terminal window or an Anaconda Prompt.

   #. Type: ``conda ins``, and then press the Tab key.

      The command completes to:

      .. code-block:: bash

         conda install

To get tab completion in zsh, see `conda-zsh-completion
<https://github.com/esc/conda-zsh-completion>`_.
