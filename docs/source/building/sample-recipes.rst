Sample recipes
==============

The first two sample recipes, Boost and libtiff, are examples of non-python libraries, meaning, they don’t require python to run or build. This illustrates the flexibility of conda in being able to build things that aren’t python related.

`boost <https://github.com/conda/conda-recipes/tree/master/boost>`_ is an example
of a popular programming library and illustrates the use of selectors in a recipe.

`libtiff <https://github.com/conda/conda-recipes/tree/master/libtiff>`_ is another
example of a compiled library. This shows how conda is able to apply patches to source directories before building the package.

`msgpack <https://github.com/conda/conda-recipes/tree/master/python/msgpack>`_,
`blosc <https://github.com/conda/conda-recipes/tree/master/python/blosc>`_, and
`cytoolz <https://github.com/conda/conda-recipes/tree/master/python/cytoolz>`_ are examples
of Python libraries with extensions.

`toolz <https://github.com/conda/conda-recipes/tree/master/python/toolz>`_,
`sympy <https://github.com/conda/conda-recipes/tree/master/python/sympy>`_,
`six <https://github.com/conda/conda-recipes/tree/master/python/six>`_, and
`gensim <https://github.com/conda/conda-recipes/tree/master/python/gensim>`_ are
examples of Python-only libraries.

Gensim works on Python 2, and all the others work on both Python 2 and Python 3.
