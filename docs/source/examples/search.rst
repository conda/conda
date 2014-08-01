.. _search_example:

Search
------

``conda search`` is a versatile option that can be used to explore packages available from known repositories or installed locally.

In the first example, we want to simply search for SciPy and see if it is in
conda's list of packages.

.. code-block:: bash

    $ conda search scipy
    scipy                        0.11.0               np17py33_1  
                                 0.11.0               np15py26_1  
                                 0.11.0               np16py27_1  
                                 0.11.0               np17py27_1  
                                 0.11.0               np16py26_1  
                                 0.11.0               np17py26_1  
                                 0.11.0               np15py27_1  
                                 0.12.0b1             np17py27_0  
                                 0.12.0b1             np17py26_0  
                                 0.12.0              np15py27_p0  [mkl]
                                 0.12.0               np15py27_0  
                                 0.12.0               np16py26_0  
                                 0.12.0              np15py26_p0  [mkl]
                                 0.12.0              np17py26_p0  [mkl]
                                 0.12.0              np16py27_p0  [mkl]
                                 0.12.0               np16py27_0  
                                 0.12.0               np17py27_0  
                              *  0.12.0              np17py27_p0  [mkl]
                                 ...

Notice the asterisk in the above example; this indicates the currently installed version of the package.

In this next example, we will refine our search a bit.  With ``^l.*py$``, we want to find any packages
that begin with ``l`` followed by any number of characters, and ending with ``py``.

.. code-block:: bash

    $ conda search ^l.*py$
      llvmpy                       0.8.3.dev                py26_0  
                                   0.8.3.dev                py27_0  
                                   0.8.3                    py27_0  
                                   0.8.3                    py26_0  
                                   0.8.4.dev                py27_0  
                                   0.8.4.dev                py26_0  
                                   0.9                      py26_0  
                                   0.9                      py27_0  
                                   0.10.0                   py27_0  
                                   ...

.. note::

  The previous example (and any others that involve regular expressions) may not work correctly on a Windows system unless the regular expression pattern is enclosed in quotation marks.  For this reason,
  all regular expressions on the command line should be enclosed in quotes.

  For example:

  .. code-block:: powershell

    D:\Test>conda search "^l.*py$"


While the previous examples have illustrated conda's basic usefulness, they have only scratched
the surface of what this option can do.

For this example, we will use an environment containing *scipy=0.11.0*, *numpy=1.7*, *python=2.7* and their dependencies.
Using the prefix option (``-p``), we can select an environment, and search for all packages that are compatible with it.

.. code-block:: bash

    $ conda search -p ~/anaconda/envs/onlyScipy/

      _license                     1.0                     py27_p0  
                                   1.1                      py27_0  
      accelerate                   1.0.0               np17py26_p0  
                                   1.0.0               np15py26_p0  
                                   1.0.0               np16py27_p0  
                                   1.0.0               np16py26_p0  
                                   1.0.0               np15py27_p0  
                                   1.0.0               np17py33_p0  
                                   1.0.0               np17py27_p0  
                                   1.0.1               np15py27_p0  
                                   
                                   ...

      xlwt                         0.7.4                    py26_0  
                                   0.7.4                    py27_0  
                                   0.7.5                    py27_0  
                                   0.7.5                    py26_0  
      yaml                         0.1.4                         0  
                                   0.1.4                         1  
      zeromq                       2.2.0                         0  
                                   2.2.0                         1  
      zlib                         1.2.7                         0  
                                *  1.2.7                         1  
      zope.interface               4.0.5                    py27_0  
                                   4.0.5                    py26_0  
                                   4.0.5                    py33_0  

It is also possible to get the same output as the above example by using the name option (``-n``) with the name of an Anaconda environment.
