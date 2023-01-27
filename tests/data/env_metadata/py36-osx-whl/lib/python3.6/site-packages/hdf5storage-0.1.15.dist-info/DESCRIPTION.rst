Overview
========

This Python package provides high level utilities to read/write a
variety of Python types to/from HDF5 (Heirarchal Data Format) formatted
files. This package also provides support for MATLAB MAT v7.3 formatted
files, which are just HDF5 files with a different extension and some
extra meta-data.

All of this is done without pickling data. Pickling is bad for security
because it allows arbitrary code to be executed in the interpreter. One
wants to be able to read possibly HDF5 and MAT files from untrusted
sources, so pickling is avoided in this package.

The package's documetation is found at
http://pythonhosted.org/hdf5storage/

The package's source code is found at
https://github.com/frejanordsiek/hdf5storage

The package is licensed under a 2-clause BSD license
(https://github.com/frejanordsiek/hdf5storage/blob/master/COPYING.txt).

Installation
============

Dependencies
------------

This package only supports Python >= 2.6.

This package requires the numpy and h5py (>= 2.1) packages to run. Note
that full functionality requires h5py >= 2.3. An optional dependency is
the scipy package.

Installing by pip
-----------------

This package is on `PyPI <https://pypi.python.org/pypi/hdf5storage>`_.
To install hdf5storage using pip, run the command::

    pip install hdf5storage

Installing from Source
----------------------

To install hdf5storage from source, download the package and then
install the dependencies ::

    pip install -r requirements.txt

Then to install the package, run the command with Python ::

    python setup.py install

Running Tests
-------------

For testing, the package nose (>= 1.0) is required as well as unittest2
on Python 2.6. There are some tests that require Matlab and scipy to be
installed and be in the executable path. Not having them means that
those tests cannot be run (they will be skipped) but all the other
tests will run. To install all testing dependencies, other than scipy,
run ::

    pip install -r requirements_tests.txt.

To run the tests ::

    python setup.py nosetests


Building Documentation
----------------------

The documentation additionally requires sphinx (>= 1.7). The
documentation dependencies can be installed by ::

    pip install -r requirements_doc.txt

To build the documentation ::

    python setup.py build_sphinx

Python 2
========

This package was designed and written for Python 3, with Python 2.7 and
2.6 support added later. This does mean that a few things are a little
clunky in Python 2. Examples include requiring ``unicode`` keys for
dictionaries, the ``int`` and ``long`` types both being mapped to the
Python 3 ``int`` type, etc. The storage format's metadata looks more
familiar from a Python 3 standpoint as well.

The documentation is written in terms of Python 3 syntax and types
primarily. Important Python 2 information beyond direct translations of
syntax and types will be pointed out.

Hierarchal Data Format 5 (HDF5)
===============================

HDF5 files (see http://www.hdfgroup.org/HDF5/) are a commonly used file
format for exchange of numerical data. It has built in support for a
large variety of number formats (un/signed integers, floating point
numbers, strings, etc.) as scalars and arrays, enums and compound types.
It also handles differences in data representation on different hardware
platforms (endianness, different floating point formats, etc.). As can
be imagined from the name, data is represented in an HDF5 file in a
hierarchal form modelling a Unix filesystem (Datasets are equivalent to
files, Groups are equivalent to directories, and links are supported).

This package interfaces HDF5 files using the h5py package
(http://www.h5py.org/) as opposed to the PyTables package
(http://www.pytables.org/).

MATLAB MAT v7.3 file support
============================

MATLAB (http://www.mathworks.com/) MAT files version 7.3 and later are
HDF5 files with a different file extension (``.mat``) and a very
specific set of meta-data and storage conventions. This package provides
read and write support for a limited set of Python and MATLAB types.

SciPy (http://scipy.org/) has functions to read and write the older MAT
file formats. This package has functions modeled after the
``scipy.io.savemat`` and ``scipy.io.loadmat`` functions, that have the
same names and similar arguments. The dispatch to the SciPy versions if
the MAT file format is not an HDF5 based one.

Supported Types
===============

The supported Python and MATLAB types are given in the tables below.
The tables assume that one has imported collections and numpy as::

    import collections as cl
    import numpy as np

The table gives which Python types can be read and written, the first
version of this package to support it, the numpy type it gets
converted to for storage (if type information is not written, that
will be what it is read back as) the MATLAB class it becomes if
targetting a MAT file, and the first version of this package to
support writing it so MATlAB can read it.

===============  =======  ==========================  ===========  ==============
Python                                                MATLAB
----------------------------------------------------  ---------------------------
Type             Version  Converted to                Class        Version
===============  =======  ==========================  ===========  ==============
bool             0.1      np.bool\_ or np.uint8       logical      0.1 [1]_
None             0.1      ``np.float64([])``          ``[]``       0.1
int [2]_ [3]_    0.1      np.int64 [2]_               int64        0.1
long [3]_ [4]_   0.1      np.int64                    int64        0.1
float            0.1      np.float64                  double       0.1
complex          0.1      np.complex128               double       0.1
str              0.1      np.uint32/16                char         0.1 [5]_
bytes            0.1      np.bytes\_ or np.uint16     char         0.1 [6]_
bytearray        0.1      np.bytes\_ or np.uint16     char         0.1 [6]_
list             0.1      np.object\_                 cell         0.1
tuple            0.1      np.object\_                 cell         0.1
set              0.1      np.object\_                 cell         0.1
frozenset        0.1      np.object\_                 cell         0.1
cl.deque         0.1      np.object\_                 cell         0.1
dict             0.1                                  struct       0.1 [7]_
np.bool\_        0.1                                  logical      0.1
np.void          0.1
np.uint8         0.1                                  uint8        0.1
np.uint16        0.1                                  uint16       0.1
np.uint32        0.1                                  uint32       0.1
np.uint64        0.1                                  uint64       0.1
np.uint8         0.1                                  int8         0.1
np.int16         0.1                                  int16        0.1
np.int32         0.1                                  int32        0.1
np.int64         0.1                                  int64        0.1
np.float16 [8]_  0.1
np.float32       0.1                                  single       0.1
np.float64       0.1                                  double       0.1
np.complex64     0.1                                  single       0.1
np.complex128    0.1                                  double       0.1
np.str\_         0.1      np.uint32/16                char/uint32  0.1 [5]_
np.bytes\_       0.1      np.bytes\_ or np.uint16     char         0.1 [6]_
np.object\_      0.1                                  cell         0.1
np.ndarray       0.1      [9]_ [10]_                  [9]_ [10]_   0.1 [9]_ [11]_
np.matrix        0.1      [9]_                        [9]_         0.1 [9]_
np.chararray     0.1      [9]_                        [9]_         0.1 [9]_
np.recarray      0.1      structured np.ndarray       [9]_ [10]_   0.1 [9]_
===============  =======  ==========================  ===========  ==============

.. [1] Depends on the selected options. Always ``np.uint8`` when doing
       MATLAB compatiblity, or if the option is explicitly set.
.. [2] In Python 2.x, it may be read back as a ``long`` if it can't fit
       in the size of an ``int``.
.. [3] Must be small enough to fit into an ``np.int64``.
.. [4] Type found only in Python 2.x. Python 2.x's ``long`` and ``int``
       are unified into a single ``int`` type in Python 3.x. Read as an
       ``int`` in Python 3.x.
.. [5] Depends on the selected options and whether it can be converted
       to UTF-16 without using doublets. If the option is explicity set
       (or implicitly when doing MATLAB compatibility) and it can be
       converted to UTF-16 without losing any characters that can't be
       represented in UTF-16 or using UTF-16 doublets (MATLAB doesn't
       support them), then it is written as ``np.uint16`` in UTF-16
       encoding. Otherwise, it is stored at ``np.uint32`` in UTF-32
       encoding.
.. [6] Depends on the selected options. If the option is explicitly set
       (or implicitly when doing MATLAB compatibility), it will be
       stored as ``np.uint16`` in UTF-16 encoding unless it has
       non-ASCII characters in which case a ``NotImplementedError`` is
       thrown). Otherwise, it is just written as ``np.bytes_``.
.. [7] All keys must be ``str`` in Python 3 or ``unicode`` in Python 2.
       They cannot have null characters (``'\x00'``) or forward slashes
       (``'/'``) in them.
.. [8] ``np.float16`` are not supported for h5py versions before
       ``2.2``.
.. [9] Container types are only supported if their underlying dtype is
       supported. Data conversions are done based on its dtype.
.. [10] Structured ``np.ndarray`` s (have fields in their dtypes) can be
        written as an HDF5 COMPOUND type or as an HDF5 Group with
        Datasets holding its fields (either the values directly, or as
        an HDF5 Reference array to the values for the different elements
        of the data). Can only be written as an HDF5 COMPOUND type if
        none of its field are of dtype ``'object'``. Field names cannot
        have null characters (``'\x00'``) and, when writing as an HDF5
        GROUP, forward slashes (``'/'``) in them.
.. [11] Structured ``np.ndarray`` s with no elements, when written like a
        structure, will not be read back with the right dtypes for their
        fields (will all become 'object').

This table gives the MATLAB classes that can be read from a MAT file,
the first version of this package that can read them, and the Python
type they are read as.

===============  =======  =================================
MATLAB Class     Version  Python Type
===============  =======  =================================
logical          0.1      np.bool\_
single           0.1      np.float32 or np.complex64 [12]_
double           0.1      np.float64 or np.complex128 [12]_
uint8            0.1      np.uint8
uint16           0.1      np.uint16
uint32           0.1      np.uint32
uint64           0.1      np.uint64
int8             0.1      np.int8
int16            0.1      np.int16
int32            0.1      np.int32
int64            0.1      np.int64
char             0.1      np.str\_
struct           0.1      structured np.ndarray
cell             0.1      np.object\_
canonical empty  0.1      ``np.float64([])``
===============  =======  =================================

.. [12] Depends on whether there is a complex part or not.


Versions
========

0.1.15. Bugfix release that fixed the following bugs.
        * Issue #68. Fixed bug where ``str`` and ``numpy.unicode_``
          strings (but not ndarrays of them) were saved in
          ``uint32`` format regardless of the value of
          ``Options.convert_numpy_bytes_to_utf16``.
        * Issue #70. Updated ``setup.py`` and ``requirements.txt`` to specify
          the maximum versions of numpy and h5py that can be used for specific
          python versions (avoid version with dropped support).
        * Issue #71. Fixed bug where the ``'python_fields'`` attribute wouldn't
          always be written when doing python metadata for data written in
          a struct-like fashion. The bug caused the field order to not be
          preserved when writing and reading.
        * Fixed an assertion in the tests to handle field re-ordering when
          no metadata is used for structured dtypes that only worked on
          older versions of numpy.
        * Issue #72. Fixed bug where python collections filled with ndarrays
          that all have the same shape were converted to multi-dimensional
          object ndarrays instead of a 1D object ndarray of the elements.

0.1.14. Bugfix release that also added a couple features.
        * Issue #45. Fixed syntax errors in unicode strings for Python
          3.0 to 3.2.
        * Issues #44 and #47. Fixed bugs in testing of conversion and
          storage of string types.
        * Issue #46. Fixed raising of ``RuntimeWarnings`` in tests due
          to signalling NaNs.
        * Added requirements files for building documentation and
          running tests.
        * Made it so that Matlab compatability tests are skipped if
          Matlab is not found, instead of raising errors.

0.1.13. Bugfix release fixing the following bug.
        * Issue #36. Fixed bugs in writing ``int`` and ``long`` to HDF5
          and their tests on 32 bit systems.

0.1.12. Bugfix release fixing the following bugs. In addition, copyright years were also updated and notices put in the Matlab files used for testing.
        * Issue #32. Fixed transposing before reshaping ``np.ndarray``
          when reading from HDF5 files where python metadata was stored
          but not Matlab metadata.
        * Issue #33. Fixed the loss of the number of characters when
          reading empty numpy string arrays.
        * Issue #34. Fixed a conversion error when ``np.chararray`` are
          written with Matlab metadata.

0.1.11. Bugfix release fixing the following.
        * Issue #30. Fixed ``loadmat`` not opening files in read mode.

0.1.10. Minor feature/performance fix release doing the following.
        * Issue #29. Added ``writes`` and ``reads`` functions to write
          and read more than one piece of data at a time and made
          ``savemat`` and ``loadmat`` use them to increase performance.
          Previously, the HDF5 file was being opened and closed for
          each piece of data, which impacted performance, especially
	  for large files.

0.1.9. Bugfix and minor feature release doing the following.
       * Issue #23. Fixed bug where a structured ``np.ndarray`` with
         a field name of ``'O'`` could never be written as an
         HDF5 COMPOUND Dataset (falsely thought a field's dtype was
         object).
       * Issue #6. Added optional data compression and the storage of
         data checksums. Controlled by several new options.

0.1.8. Bugfix release fixing the following two bugs.
       * Issue #21. Fixed bug where the ``'MATLAB_class'`` Attribute is
         not set when writing ``dict`` types when writing MATLAB
         metadata.
       * Issue #22. Fixed bug where null characters (``'\x00'``) and
         forward slashes (``'/'``) were allowed in ``dict`` keys and the
         field names of structured ``np.ndarray`` (except that forward
         slashes are allowed when the
         ``structured_numpy_ndarray_as_struct`` is not set as is the
         case when the ``matlab_compatible`` option is set). These
         cause problems for the ``h5py`` package and the HDF5 library.
         ``NotImplementedError`` is now thrown in these cases.

0.1.7. Bugfix release with an added compatibility option and some added test code. Did the following.
       * Fixed an issue reading variables larger than 2 GB in MATLAB
         MAT v7.3 files when no explicit variable names to read are
         given to ``hdf5storage.loadmat``. Fix also reduces memory
         consumption and processing time a little bit by removing an
         unneeded memory copy.
       * ``Options`` now will accept any additional keyword arguments it
         doesn't support, ignoring them, to be API compatible with future
         package versions with added options.
       * Added tests for reading data that has been compressed or had
         other HDF5 filters applied.

0.1.6. Bugfix release fixing a bug with determining the maximum size of a Python 2.x ``int`` on a 32-bit system.

0.1.5. Bugfix release fixing the following bug.
       * Fixed bug where an ``int`` could be stored that is too big to
         fit into an ``int`` when read back in Python 2.x. When it is
         too big, it is converted to a ``long``.
       * Fixed a bug where an ``int`` or ``long`` that is too big to
	 big to fit into an ``np.int64`` raised the wrong exception.
       * Fixed bug where fields names for structured ``np.ndarray`` with
         non-ASCII characters (assumed to be UTF-8 encoded in
         Python 2.x) can't be read or written properly.
       * Fixed bug where ``np.bytes_`` with non-ASCII characters can
         were converted incorrectly to UTF-16 when that option is set
         (set implicitly when doing MATLAB compatibility). Now, it throws
         a ``NotImplementedError``.

0.1.4. Bugfix release fixing the following bugs. Thanks goes to `mrdomino <https://github.com/mrdomino>`_ for writing the bug fixes.
       * Fixed bug where ``dtype`` is used as a keyword parameter of
         ``np.ndarray.astype`` when it is a positional argument.
       * Fixed error caused by ``h5py.__version__`` being absent on
         Ubuntu 12.04.

0.1.3. Bugfix release fixing the following bug.
       * Fixed broken ability to correctly read and write empty
         structured ``np.ndarray`` (has fields).

0.1.2. Bugfix release fixing the following bugs.
       * Removed mistaken support for ``np.float16`` for h5py versions
         before ``2.2`` since that was when support for it was
         introduced.
       * Structured ``np.ndarray`` where one or more fields is of the
         ``'object'`` dtype can now be written without an error when
         the ``structured_numpy_ndarray_as_struct`` option is not set.
         They are written as an HDF5 Group, as if the option was set.
       * Support for the ``'MATLAB_fields'`` Attribute for data types
         that are structures in MATLAB has been added for when the
         version of the h5py package being used is ``2.3`` or greater.
         Support is still missing for earlier versions (this package
         requires a minimum version of ``2.1``).
       * The check for non-unicode string keys (``str`` in Python 3 and
         ``unicode`` in Python 2) in the type ``dict`` is done right
         before any changes are made to the HDF5 file instead of in the
         middle so that no changes are applied if an invalid key is
         present.
       * HDF5 userblock set with the proper metadata for MATLAB support
         right at the beginning of when data is being written to an HDF5
         file instead of at the end, meaning the writing can crash and
         the file will still be a valid MATLAB file.

0.1.1. Bugfix release fixing the following bugs.
       * ``str`` is now written like ``numpy.str_`` instead of
         ``numpy.bytes_``.
       * Complex numbers where the real or imaginary part are ``nan``
         but the other part are not are now read correctly as opposed
         to setting both parts to ``nan``.
       * Fixed bugs in string conversions on Python 2 resulting from
         ``str.decode()`` and ``unicode.encode()`` not taking the same
         keyword arguments as in Python 3.
       * MATLAB structure arrays can now be read without producing an
         error on Python 2.
       * ``numpy.str_`` now written as ``numpy.uint16`` on Python 2 if
         the ``convert_numpy_str_to_utf16`` option is set and the
         conversion can be done without using UTF-16 doublets, instead
         of always writing them as ``numpy.uint32``.

0.1. Initial version.


