.. _list_example:

List
----

``conda list -p`` shows the linked packages and their versions in a specific 
environment directory. ``--prefix`` also works.  If no prefix is provided,
conda will look in the default environment.

.. code-block:: bash

    $ conda list -p ~/envs/test2
    nose                      1.1.2
    numpy                     1.6.2
    python                    2.7.3
    readline                  6.2
    sqlite                    3.7.13
    zlib                      1.2.7

In this next example, we leave off the prefix and search for packages starting with ``py`` in the default directory.


.. code-block:: bash

    $ conda list ^py
    packages and versions matching the expression '^py' in environment at /Users/test/anaconda:
    py                        2.4.12
    pyaudio                   0.2.6
    pycurl                    7.19.0
    pyflakes                  0.5.0
    pygments                  1.5
    pysal                     1.4.0
    pysam                     0.6
    pyside                    1.1.2
    pytables                  2.4.0
    pytest                    2.3.3
    python                    2.7.3
    python.app                1.0
    pytz                      2012d
    pyyaml                    3.10
    pyzmq                     2.2.0.1

.. note::

  The previous example (and any others that involve regular expressions) may not work correctly on a Windows system unless the regular expression pattern is enclosed in quotation marks.  For this reason,
  all regular expressions on the command line should be enclosed in quotes.

  For example:

  .. code-block:: powershell

    D:\Test>conda list “^py”
    packages and versions matching the expression ‘^py’ in environment at C:\Anaconda:
    py                        1.4.12
    pyaudio                   0.2.6
    ...
    
With this final example, we will use a more complex search expression to illustrate conda's
list capabilities.

.. code-block:: bash

  $ conda list ^m.*lib$
  packages and versions matching the expression '^m.*lib$' in environment at /Users/test/anaconda:
  matplotlib                1.2.0



