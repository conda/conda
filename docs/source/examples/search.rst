.. _search_example:

Search
------

``conda search`` is a versatile conda option that can be used in a variety of ways.

In the first example, we want to simply search for scipy and see if it is in
conda's list of packages.  We will also show its dependencies.

.. code-block:: bash

    $ conda search -s scipy
    12 matches found:

       package: scipy-0.11.0rc2 [pro]
          arch: x86_64
      filename: scipy-0.11.0rc2-np16py26_pro0.tar.bz2
           md5: 177898fbbd82196f066968ff03079a1d
      requires:
            numpy-1.6
            python-2.6

       ...

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np17py27_pro0.tar.bz2
           md5: f4cbc54250e4c3d18ab04b60c6fe9f17
      requires:
            numpy-1.7
            python-2.7

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np16py26_pro0.tar.bz2
           md5: 009960638acadf845f1249f1f3888e18
      requires:
            numpy-1.6
            python-2.6

       package: scipy-0.11.0 [pro]
          arch: x86_64
      filename: scipy-0.11.0-np15py27_pro0.tar.bz2
           md5: 7a7ce190a0a221af74b89183687d1a5b
      requires:
            numpy-1.5
            python-2.7

In this next example, we will refine our search a bit.  With ``^l.*py$`` we want to find any packages
that begin with ``l`` followed by any number of characters, and ending with ``py``.

.. code-block:: bash

    $ conda search -s ^l.*py$
    6 matches found:

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py27_0.tar.bz2
           md5: 3d154f02354b22ac2e0ad76e73073f4e
      requires:
            llvm-3.1
            python-2.7

       package: llvmpy-0.8.3.dev 
          arch: x86_64
      filename: llvmpy-0.8.3.dev-py26_0.tar.bz2
           md5: 6cebbf5e402a9c5a6d3fba29182f980d
      requires:
            llvm-3.1
            python-2.6

        ...

       package: llvmpy-0.8.4.dev 
          arch: x86_64
      filename: llvmpy-0.8.4.dev-py27_0.tar.bz2
           md5: ce8b92705249d638850528bdddc27dc8
      requires:
            llvm-3.1
            python-2.7

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py26_0.tar.bz2
           md5: d0edc507d66dd34e32dc9d277c68fe36
      requires:
            llvm-3.1
            python-2.6

.. note::

  The previous example (and any others that involve regular expressions) may not work correctly on a Windows system unless the regular expression pattern is enclosed in quotation marks.  For this reason,
  all regular expressions on the command line should be enclosed in quotes.

  For example:

  .. code-block:: powershell

    D:\Test>conda search -s "^l.*py$"
    6 matches found:

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py27_0.tar.bz2
           md5: 3d154f02354b22ac2e0ad76e73073f4e
      requires:
            llvm-3.1
            python-2.7
            
        ...

       package: llvmpy-0.8.3 
          arch: x86_64
      filename: llvmpy-0.8.3-py26_0.tar.bz2
           md5: d0edc507d66dd34e32dc9d277c68fe36
      requires:
            llvm-3.1
            python-2.6


While the previous examples have illustrated conda's basic usefulness, they have only scratched
the surface of what this option can do.

For this example, we will use an environment containing scipy=0.11.0, numpy=1.7, python=2.7 and their dependencies.
Using the prefix option (``-p``), we can select an environment, and search for all packages that are compatible with it.

.. code-block:: bash

    $ conda search -p ~/anaconda/envs/onlyScipy/

       package: anaconda-1.1 [ce]
          arch: x86_64
      filename: anaconda-1.1-np17py27_ce0.tar.bz2
           md5: 1eda25b89e4a6ec9293840e07f2aa89b

       package: anaconda-1.1.4 [pro]
          arch: x86_64
      filename: anaconda-1.1.4-np15py26_pro0.tar.bz2
           md5: c38095a04aeca3838c622b86c632235d

       package: anaconda-1.1 [pro]
          arch: x86_64
      filename: anaconda-1.1-np15py26_pro0.tar.bz2
           md5: 683498ea22ca6675b7f1281c9dc62bb3

       package: anaconda-1.1.4 [pro]
          arch: x86_64
      filename: anaconda-1.1.4-np17py27_pro0.tar.bz2
           md5: e53725e6c03427c8445cc966a0b877d3


    ...

       package: wakaridata-1.0 
          arch: x86_64
      filename: wakaridata-1.0-py26_0.tar.bz2
           md5: 36e06413d215e9db75ffda561ecd6642

       package: wakaridata-1.0 
          arch: x86_64
      filename: wakaridata-1.0-py27_0.tar.bz2
           md5: 5df6f71c1764ab83c3c82e589fd84092

       package: werkzeug-0.8.3 
          arch: x86_64
      filename: werkzeug-0.8.3-py27_0.tar.bz2
           md5: 0e0775f16145096081f0ff2c60e7334e

       package: werkzeug-0.8.3 
          arch: x86_64
      filename: werkzeug-0.8.3-py26_0.tar.bz2
           md5: aff1d6a44c922e3f9a27ae35949b6866

       package: wiserf-0.9 
          arch: x86_64
      filename: wiserf-0.9-np17py27_0.tar.bz2
           md5: 8a6c5c81248c3fa68c9197c7f5742245

       package: yaml-0.1.4 
          arch: x86_64
      filename: yaml-0.1.4-0.tar.bz2
           md5: 8d576ab603ce38ef619d59f71875e8d7

       package: zeromq-2.2.0 
          arch: x86_64
      filename: zeromq-2.2.0-0.tar.bz2
           md5: 992590aa055cb67c00e8460e81ae49f8

       package: zlib-1.2.7 
          arch: x86_64
      filename: zlib-1.2.7-0.tar.bz2
           md5: 0841a23e33e22d0b139620dc47a37223


