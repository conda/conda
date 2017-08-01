======================
Using shared libraries
======================

Shared libraries are libraries that are loosely coupled to the
programs and extensions that depend on them. When loading an
executable into memory, an operating system finds all dependent
shared libraries and links them to the executable so that it can
run.

Windows, macOS and Linux all provide a way to build executables
and libraries that contain links to the shared libraries they
depend on, instead of directly linking the libraries themselves.


Shared libraries in Windows
===========================

Unlike macOS and Linux, Windows does not have the concept of
embedding links into binaries. Instead, Windows depends primarily
on searching directories for matching filenames, as documented in
`Search Path Used by Windows to Locate a DLL
<https://msdn.microsoft.com/en-us/library/7d83bc18.aspx>`_.

There is an alternate configuration, called `side-by-side
assemblies <https://en.wikipedia.org/wiki/Side-by-side_assembly>`_,
that requires specification of DLL versions in either an embedded
manifest or an appropriately named XML file alongside the binary
in question. Conda does not currently use side-by-side
assemblies, but it may turn towards that in the future to resolve
complications with multiple versions of the same library on the
same system.

For now, most DLLs are installed into ``(install prefix)\\Library\\bin``.
This path is added to ``os.environ["PATH"]`` for all Python processes,
so that DLLs can be located, regardless of the value of the
system's PATH environment variable.

NOTE: PATH is searched from left to right, with the first DLL
name match being picked up, in the absence of a manifest
specifying otherwise. This means that installing software with
other matching DLLs may give you a system that crashes in
unpredictable ways. When troubleshooting or asking for support on
Windows, always consider PATH as a potential source of issues.


Shared libraries in macOS and Linux
====================================

In macOS and Linux, dynamic links are discovered in a similar
manner to the way that Python modules are discovered via
PYTHONPATH, and executables are discovered via PATH. A list of
search locations is made, and then the library objects are
searched for in the search locations. By default, as well as by
design, the system dynamic linker does not have any special
preference for the conda environment ``lib`` directories.

You can specify both absolute links and relative links. If the
links are absolute paths, such as ``/Users/jsmith/my_build_env``,
the library works only on a system where that exact path exists.
Therefore, relative links are preferred in conda packages.

Relative links require a special variable in the link itself:

* On Linux, the $ORIGIN variable allows you to specify "relative
  to this file as it is being executed".

* On macOS, the variables are:

  * @rpath---Allows you to set relative links from the system
    load paths.

  * @loader_path---Equivalent to $ORIGIN.

  * @executable_path---Supports the Apple ``.app`` directory
    approach, where libraries know where they live relative to
    their calling application.

Conda build uses @loader_path on macOS and $ORIGIN on Linux
because we install into a common root directory and can assume
that other libraries are also installed into that root. The use
of the variables allows you to build relocatable binaries that
can be built on one system and sent everywhere.

On Linux, ``conda-build`` modifies any shared libraries or
generated executables to use a relative dynamic link by calling
the patchelf tool. On macOS, the install_name_tool tool is used.

CAUTION: Setting LD_LIBRARY_PATH on Linux or DYLD_LIBRARY_PATH on
macOS can interfere with this because the dynamic linker
short-circuits link resolution by first looking at
LD_LIBRARY_PATH.

EXAMPLE: You install an old version of libcurl into your conda
environment due to some compatibility issues with the code you're
using. Then, you set
``export LD_LIBRARY_PATH=/home/jsmith/envs/curl_env/lib``. From
that point on, every program that you execute in that session
will favor this libcurl to your system libcurl, because it is now
effectively at the "front" of the dynamic load path.

Including conda environment paths in LD_LIBRARY_PATH or
DYLD_LIBRARY_PATH is not recommended.
