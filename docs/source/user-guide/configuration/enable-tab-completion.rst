=======================
Enabling tab completion
=======================

Conda versions up to 4.3 supports tab completion in Bash shells via the argcomplete
package. Bash tab completion has been removed starting with version 4.4.0.

To enable tab completion in your Bash shell:

#. Make sure that argcomplete is installed:

   .. code-block:: bash

      conda install argcomplete

#. Add the following code to your bash profile:

   .. code-block:: bash

      eval "$(register-python-argcomplete conda)"

#. Test it:

   #. Open a new terminal window or an Anaconda Prompt.

   #. Type: ``conda ins``, and then press the Tab key.

      The command completes to:

      .. code-block:: bash

         conda install

To get tab completion in Zsh, see `conda-zsh-completion
<https://github.com/conda-incubator/conda-zsh-completion>`_.
