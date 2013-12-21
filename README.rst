|

Here are mainly ``addons/changes`` for the nice ``conda: package management tool``. These are additional features I would like to see in the ``main conda package``. 
Hopefully one or the other idea makes it back to the original codebase and can be removed from here.


`For Installation see INSTALL.rst <INSTALL.rst>`_


ADDONS 
======

|

#====== CONDA_ADDONS: COMMON DIRS
---------------------------------

|

conda_recipes_dir
=================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_RECIPES_DIR:
    # directory in which conda recipes are located:
    # useful if one wants one common conda_recipes folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda_recipes)
    conda_recipes_dir: /home/0_CONDA_RELATED_0/conda-recipes


conda_repo_dir
==============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_REPO_DIR:
    # directory in which conda build packages are located: in the 
    # architecture subfolders
    # useful if one wants one common conda_repo folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda-bld)
    conda_repo_dir: /home/0_CONDA_RELATED_0/conda-repo


conda_sources_dir
=================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CONDA_REPO_DIR:
    # directory in which conda build packages are located: in the 
    # architecture subfolders
    # useful if one wants one common conda_repo folder for 
    # different conda installation (defaults to: *CONDA ROOT/conda-bld)
    conda_repo_dir: /home/0_CONDA_RELATED_0/conda-repo

|

#====== CONDA_ADDONS: Overwrite meta.yaml settings
--------------------------------------------------

|

overwrite_build_num
===================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # OVERWRITE_BUILD_NUM:
    # if this is configure: any build number will be overwritten
    # (default 0 or the one specified in the meta.yaml)
    # useful if one wants to rebuild all packages and init them with the
    # same build number
    overwrite_build_num: 1


overwrite_build_string
======================

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # OVERWRITE_BUILD_STRING:
    # if this is configure: any build string will be overwritten
    # (default '' (empty string or the one specified in the meta.yaml)
    # useful if one wants to rebuild all packages and init them with the
    # same build string: e.g. which lunux distribution it was compiled on
    overwrite_build_string: build_on_debian_wheezy_py33

|

#====== CONDA_ADDONS: set build/compile/make flags
--------------------------------------------------

#IMPORTANT: all of them can be overwritten in the build.sh
#   but this should only be done in special cases as it will nullify
#   the options here: except were noted

|

`Some related info:`

    * use: You can invoke GCC with "-Q --help=optimizers" to find out the exact 
    * set of optimizations that are enabled
    * Most optimizations are only enabled if an -O level is set on the command 
    * line. Otherwise they are disabled even if individual optimization flags 
    * are specified. 
    * some related links of interest
    * http://gcc.gnu.org/onlinedocs/_  
    * http://gcc.gnu.org/onlinedocs/gcc-4.8.2/gcc/Overall-Options.html#Overall-Options
    * http://gcc.gnu.org/onlinedocs/gcc-4.8.2/gcc/Optimize-Options.html#Optimize-Options
    * http://gcc.gnu.org/onlinedocs/gcc/Submodel-Options.html#Submodel-Options
    * https://wiki.gentoo.org/wiki/GCC_optimization
    * http://www.gnu.org/software/make/manual/html_node/Overriding.html
    * http://www.ilkda.com/compile/Environment_Variables.htm
    * http://linuxreviews.org/man/make.conf/
    * https://developer.apple.com/library/mac/documentation/porting/conceptual/portingunix/compiling/compiling.html
    * http://faculty.washington.edu/rjl/uwamath583s11/sphinx/notes/html/gfortran_flags.html

|

build_cppflags
==============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CPPFLAGS:         
    # C/C++/Objective C preprocessor flags, 
    # e.g. -I<include dir> if
    # you have headers in a nonstandard directory <include dir>
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_cppflags: "-I/MyInclude"


build_cflags
============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CFLAGS:
    # C compiler flags
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_cflags: "-O2 -pipe"


build_cxxflags
==============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CXXFLAGS:
    # C++ compiler flags
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_cxxflags: "-O2 -pipe"


build_ldflags
=============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # LDFLAGS
    # LD flags: linker flags, 
    # e.g. -L<lib dir> if you have libraries in a 
    # nonstandard directory <lib dir>
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_ldflags: "-L/home/MyLib" 


build_fflags
============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # FFLAGS:
    # Fortran 77 compiler flags 
    # see http://linuxreviews.org/man/make.conf/
    #   FFLAGS is usually passed to the FORTRAN 77 compiler, 
    # and FCFLAGS to any FORTRAN compiler in more modern build systems.
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_fflags: "-Wall"     
      

build_fcflags
=============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # FCFLAGS:
    # Fortran compiler flags 
    # see http://linuxreviews.org/man/make.conf/
    #   FFLAGS is usually passed to the FORTRAN 77 compiler, 
    # and FCFLAGS to any FORTRAN compiler in more modern build systems.
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    build_fcflags: "-Wall"      
        

build_makeflags
===============

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash
      
    # MAKEFLAGS:
    # MAKE FLAGS: e.g. multi-core option: always exported
    # gnu make multi-core compile option: -j [N], --jobs[=N]  
    # Allow N jobs at once; 
    # In build.sh: usually one does not need to specify anything 
    # LINUX: on purpose: Variable is ONLY exported if configured here
    # https://www.gnu.org/software/make/manual/make.html
    build_makeflags: "-j 4"


build_chost
===========

USAGE: see `condarc_EXAMPLE file <condarc_EXAMPLE>`_

.. code-block:: bash

    # CHOST:
    # ARCH-VENDOR-OS-LIBC: can be used for cross-compiling 
    # e.g. passed on to: --host=$CHOST   or  maybe --target=$CHOST  
    # http://wiki.gentoo.org/wiki/CHOST
    # The variable is a dash-separated tuple in the form of ARCH-VENDOR-OS-LIBC. 
    # ARCH specifies the CPU architecture, VENDOR specifies the hardware platform 
    # or vendor, OS is the operating system, and LIBC is the C library to use. 
    # Only ARCH is strictly required in all cases, but - for Linux machines at
    # least - it's good practice to specify all four fields
    # LINUX: on purpose: Variable is ONLY exported if configured here
    #       IMPORTANT: one must make explicit use of this option 
    #       in the build.sh to have any effects
    # USAGE example: in build.sh: ./configure --host=$CHOST
    build_chost: "x86_64-unknown-linux-gnu"

|

#====== CONDA_ADDONS: DIVERSE ======#
-----------------------------------------

|

append build number to file
===========================

always append any build number  to the output package archive file



|
|
|

`For Installation see INSTALL.rst <INSTALL.rst>`_

peter1000: https://github.com/peter1000/
