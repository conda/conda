==============
Tab Completion
==============

``conda`` supports tab completion in bash shells via the ``argcomplete``
package. First, make sure that ``argcomplete`` is installed

.. code-block:: bash

   $ conda install argcomplete

Then add

.. code-block:: bash

   eval "$(register-python-argcomplete conda)"

to your bash profile. You can test that it works by opening a new terminal
window and typing

.. code-block:: bash

   $ conda ins<TAB>

It should complete to

.. code-block:: bash

   $ conda install

To get tab completion in zsh, see `conda-zsh-completion
<https://github.com/esc/conda-zsh-completion>`_.
