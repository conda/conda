=======================
Anaconda compiler tools
=======================

Anaconda 5.0 switched from OS-provided compiler tools to our own toolsets. This
allows improved compiler capabilities, including better security and
performance. This page describes how to use these tools and enable these
benefits.

Compiler packages
=================

Before Anaconda 5.0, compilers were installed using system tools such as XCode
or ``yum install gcc``. Now there are conda packages for Linux and macOS
compilers. Unlike the previous gcc 4.8.5 packages that included gcc, g++ and
gfortran all in the same package, these conda packages are split into separate
compilers:

Linux:

* gcc_linux-64
* gxx_linux-64
* gfortran_linux-64

macOS:

* clang_osx-64
* clangxx_osx-64
* gfortran_osx-64

A compiler's "build platform" is the platform where the compiler runs and
builds the code.

A compiler's "host platform" is the platform where the built code will finally
be hosted and run.

Notice that all of these package names end in a platform identifier which
specifies the host platform. All compiler packages are specific to both the
build platform and the host platform.

Using the compiler packages
===========================

The compiler packages can be installed with conda. Because they are designed
with (pseudo) cross-compiling in mind, all of the executables in a compiler
package are "prefixed." Instead of ``gcc``, the executable name of the compiler
you use will be something like ``x86_64-conda_cos6-linux-gnu-gcc``. These full
compiler names are shown in the build logs, recording the host platform and
helping prevent the common mistake of using the wrong compiler.

Many build tools such as ``make`` and ``cmake`` search by default for a
compiler named simply ``gcc``, so we set environment variables to point these
tools to the correct compiler.

We set these variables in conda ``activate.d`` scripts, so any environment in
which you will use the compilers must first be activated so the scripts will
run. Conda-build does this activation for you using activation hooks installed
with the compiler packages in ``CONDA_PREFIX/etc/conda/activate.d``, so no
additional effort is necessary.

You can activate the root environment with the command ``source activate root``.

macOS SDK
=========

The macOS compilers require the macOS 10.9 SDK. The SDK license prevents it
from being bundled in the conda package.

We know of two current sources for the macOS 10.9 SDK:

- https://github.com/devernay/xcodelegacy
- https://github.com/phracker/MacOSX-SDKs

We usually install this SDK at ``/opt/MacOSX10.9.sdk`` but you may install it
anywhere.

Edit your ``conda_build_config.yaml`` file to point to it, like this::

    CONDA_BUILD_SYSROOT:
      - /opt/MacOSX10.9.sdk        # [osx]

At Anaconda we have this configuration setting in a centralized
``conda_build_config.yaml`` at the root of our recipe repository. Since we run
build commands from that location, the file and the setting are used for all
recipes.

The ``conda_build_config.yaml`` search order is described further at
:ref:`conda-build-variant-config-files`.

Backward compatibility
======================

Some users want to use the latest Anaconda packages but do not yet want to use
the Anaconda compilers. To enable this, the latest Python package builds have
a default ``_sysconfigdata`` file. This file sets the compilers provided by the
system, such as ``gcc`` and ``g++``, as the default compilers. This way legacy
recipes will keep working.

Python packages also include an alternative ``_sysconfigdata`` file that sets
the Anaconda compilers as the default compilers. The Anaconda Python executable
itself is made with these Anaconda compilers.

The compiler packages set the environment variable
``_PYTHON_SYSCONFIGDATA_NAME``, which tells Python which ``_sysconfigdata`` file
to use. This variable is set at activation time using the activation hooks
described above.

The new ``_sysconfigdata`` customization system is only present in recent
versions of the Python package. Conda-build automatically tries to use the
latest Python version available in the currently configured channels, which
normally gets the latest from the default channel. If you're using something
other than conda-build while working with the new compilers, conda does not
automatically update Python, so make sure you have the correct
``_sysconfigdata`` files by updating your Python package manually.

Anaconda compilers and conda-build 3
====================================

The Anaconda 5.0 compilers and conda-build 3 are designed to work together.

Conda-build 3 defines a special jinja2 function, ``compiler()``, to make it
easy to specify compiler packages dynamically on many platforms. The
``compiler`` function takes at least one argument, the language of the compiler
to use::

    requirements:
      build:
        - {{ compiler('c') }}

"Cross-capable" recipes can be used to make packages with a host platform
different than the build platform where conda-build runs. To write cross-capable
recipes you may also need to use the "host" section in the requirements
section. In this example we set "host" to "zlib" to tell conda-build to use
the zlib in the conda environment and not the system zlib. This makes sure
conda-build uses the zlib for the host platform and not the zlib for the build
platform.

::

    requirements:
      build:
        - {{ compiler('c') }}
      host:
        - zlib

Generally the build section should include compilers and other build tools, and
the host section should include everything else, including shared libraries,
Python, and Python libraries.

Customizing the compilers
=========================

The compiler packages listed above are small packages that only include the
activation scripts and list most of the software they provide as runtime
dependencies.

This design is intended to make it easy for you to customize your own compiler
packages by copying these recipes and changing the flags. You can then edit the
``conda_build_config.yaml`` file to specify your own packages.

We have been careful to select good, general purpose, secure and fast flags.
We have also used them for all packages in Anaconda Distribution 5.0.0, except
for some minor customizations in a few recipes. When changing these flags,
remember that choosing the wrong flags can reduce security, reduce performance
and cause incompatibilities.

With that warning in mind, let's look at good ways to customize clang.

1. Download or fork the code from https://github.com/anacondarecipes/aggregate .
   The clang package recipe is in the clang folder. The main material is in the
   llvm-compilers-feedstock folder.

2. Edit ``clang/recipe/meta.yaml``::

       package:
         name: clang_{{ target_platform }}
         version: {{ version }}

   The name here does not matter but the output names below do. Conda-build
   expects any compiler to follow the BASENAME_PLATFORMNAME pattern, so it is
   important to keep the ``{{target_platform}}`` part of the name.

   ``{{ version }}`` is left as an intentionally undefined jinja2 variable. It
   is set later in ``conda_build_config.yaml``.

3. Before any packaging is done, run the build.sh script:
   https://github.com/AnacondaRecipes/aggregate/blob/master/clang/build.sh

   In this recipe, values are changed here. Those values are inserted into the
   activate scripts that are installed later.

   ::

       #!/bin/bash

       CHOST=${macos_machine}

       FINAL_CPPFLAGS="-D_FORTIFY_SOURCE=2 -mmacosx-version-min=${macos_min_version}"
       FINAL_CFLAGS="-march=core2 -mtune=haswell -mssse3 -ftree-vectorize -fPIC -fPIE -fstack-protector-strong -O2 -pipe"
       FINAL_CXXFLAGS="-march=core2 -mtune=haswell -mssse3 -ftree-vectorize -fPIC -fPIE -fstack-protector-strong -O2 -pipe -stdlib=libc++ -fvisibility-inlines-hidden -std=c++14 -fmessage-length=0"
       # These are the LDFLAGS for when the linker is being called directly, without "-Wl,"
       FINAL_LDFLAGS="-pie -headerpad_max_install_names"
       # These are the LDFLAGS for when the linker is being driven by a compiler, with "-Wl,"
       FINAL_LDFLAGS_CC="-Wl,-pie -Wl,-headerpad_max_install_names"
       FINAL_DEBUG_CFLAGS="-Og -g -Wall -Wextra -fcheck=all -fbacktrace -fimplicit-none -fvar-tracking-assignments"
       FINAL_DEBUG_CXXFLAGS="-Og -g -Wall -Wextra -fcheck=all -fbacktrace -fimplicit-none -fvar-tracking-assignments"
       FINAL_DEBUG_FFLAGS="-Og -g -Wall -Wextra -fcheck=all -fbacktrace -fimplicit-none -fvar-tracking-assignments"

       find "${RECIPE_DIR}" -name "*activate*.sh" -exec cp {} . \;

       find . -name "*activate*.sh" -exec sed -i.bak "s|@CHOST@|${CHOST}|g" "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@CPPFLAGS@|${FINAL_CPPFLAGS}|g"             "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@CFLAGS@|${FINAL_CFLAGS}|g"                 "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@DEBUG_CFLAGS@|${FINAL_DEBUG_CFLAGS}|g"     "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@CXXFLAGS@|${FINAL_CXXFLAGS}|g"             "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@DEBUG_CXXFLAGS@|${FINAL_DEBUG_CXXFLAGS}|g" "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@DEBUG_CXXFLAGS@|${FINAL_DEBUG_CXXFLAGS}|g" "{}" \;
       # find . -name "*activate*.sh" -exec sed -i.bak "s|@FFLAGS@|${FINAL_FFLAGS}|g"                 "{}" \;
       # find . -name "*activate*.sh" -exec sed -i.bak "s|@DEBUG_FFLAGS@|${FINAL_DEBUG_FFLAGS}|g"     "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@LDFLAGS@|${FINAL_LDFLAGS}|g"               "{}" \;
       find . -name "*activate*.sh" -exec sed -i.bak "s|@LDFLAGS_CC@|${FINAL_LDFLAGS_CC}|g"         "{}" \;
       find . -name "*activate*.sh.bak" -exec rm "{}" \;

4. With those changes to the activate scripts in place, it's time to move on to
   installing things. Look back at the clang folder's ``meta.yaml``. Here's
   where we change the package name. Notice what comes before the
   ``{{ target_platform }}``.

   ::

       outputs:
         - name: super_duper_clang_{{ target_platform }}
           script: install-clang.sh
           requirements:
             - clang {{ version }}

   The script reference here is another place you might add customization.
   You'll either change the contents of those install scripts, or change the
   scripts that those install scripts are installing.

   Note that we make the package ``clang`` in the main material agree in version
   with our output version. This is implicitly the same as the top-level
   recipe. The ``clang`` package sets no environment variables at all, so it
   may be difficult to use directly.

5. Let's examine the script ``install-clang.sh``::

       #!/bin/bash

       set -e -x

       CHOST=${macos_machine}

       mkdir -p "${PREFIX}"/etc/conda/{de,}activate.d/
       cp "${SRC_DIR}"/activate-clang.sh "${PREFIX}"/etc/conda/activate.d/activate_"${PKG_NAME}".sh
       cp "${SRC_DIR}"/deactivate-clang.sh "${PREFIX}"/etc/conda/deactivate.d/deactivate_"${PKG_NAME}".sh

       pushd "${PREFIX}"/bin
         ln -s clang ${CHOST}-clang
       popd

   Nothing here is too unusual.

   Activate scripts are named according to our package name so they won't
   conflict with other activate scripts.

   The symlink for clang is a clang implementation detail that sets the host
   platform.

   We define ``macos_machine`` in aggregate's ``conda_build_config.yaml``:
   https://github.com/AnacondaRecipes/aggregate/blob/master/conda_build_config.yaml#L79

   The activate scripts that are being installed are where we actually set the
   environment variables. Remember that these have been modified by build.sh.

6. With any of your desired changes in place, go ahead and build the recipe.

   You should end up with a super_duper_clang_osx-64 package. Or, if you're not
   on macOS and are modifying a different recipe, you should end up with an
   equivalent package for your platform.

Using your customized compiler package with conda-build 3
=========================================================

Remember the Jinja2 function, ``{{ compiler('c') }}``? Here's where that comes
in. Specific keys in ``conda_build_config.yaml`` are named for the language
argument to that jinja2 function. In your ``conda_build_config.yaml``, add
this::

    c_compiler:
      - super_duper_clang

Note that we're not adding the ``target_platform`` part, which is separate. You
can define that key, too::

    c_compiler:
      - super_duper_clang
    target_platform:
      - win-64

With those two keys defined, conda-build will try to use a compiler package
named ``super_duper_clang_win-64``. That package needs to exist for your native
platform. For example, if you're on macOS, your native platform is ``osx-64``.

The package subdirectory for your native platform is the build platform. The
build platform and the ``target_platform`` can be the same, and they are the
same by default, but they can also be different. When they are different,
you're cross-compiling.

If you ever needed a different compiler key for the same language, remember
that the language key is arbitrary. For example, we might want different
compilers for Python and for R within one ecosystem. On Windows the Python
ecosystem uses the Microsoft Visual C compilers, while the R ecosystem uses the
Mingw compilers.

Let's start in ``conda_build_config.yaml``::

    python_c_compiler:
      - vs2015
    r_c_compiler:
      - m2w64-gcc
    target_platform:
      - win-64

In Python recipes, you'd have::

    requirements:
      build:
        - {{ compiler('python_c') }}

In R recipes, you'd have::

    requirements:
      build:
        - {{ compiler('r_c') }}

This example is a little contrived, because the ``m2w64-gcc_win-64`` package is
not available. You'd need to create a metapackage ``m2w64-gcc_win-64`` to
point at the ``m2w64-gcc`` package, which does exist on the msys2 channel on
`repo.continuum.io <https://repo.continuum.io/>`_ .
