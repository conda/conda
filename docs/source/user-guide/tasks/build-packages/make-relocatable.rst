===========================
Making packages relocatable
===========================

Often, the most difficult thing about building a conda package is 
making it relocatable. Relocatable means that the package can be 
installed into any prefix. Otherwise, the package would be usable 
only in the environment in which it was built.

Conda build does the following things automatically to make 
packages relocatable:

* Binary object files are converted to use relative paths using
  install_name_tool on macOS and patchelf on Linux.

* Any text file without NULL bytes that contains the build prefix 
  or the placeholder prefix ``/opt/anaconda1anaconda2anaconda3`` 
  is registered in the ``info/has_prefix`` file in the package 
  metadata. When conda installs the package, any files in 
  ``info/has_prefix`` have the registered prefix replaced with 
  the install prefix. For more information, see 
  :ref:`package_metadata` .

* Any binary file containing the build prefix can automatically 
  be registered in ``info/has_prefix`` using 
  build/detect_binary_files_with_prefix in ``meta.yaml``. 
  Alternatively, individual binary files can be registered by 
  listing them in build/binary_has_prefix_files in 
  ``meta.yaml``. The registered files will have their build 
  prefix replaced with the install prefix at install time. This 
  works by padding the install prefix with null terminators, such 
  that the length of the binary file remains the same. The build 
  prefix must therefore be long enough to accommodate any 
  reasonable installation prefix. On Linux and Mac, conda build 
  pads the build prefix to 255 characters by appending 
  ``_placehold``\'s to the end of the build directory name.  

  NOTE: The prefix length was changed in conda build 2.0 from 80 
  characters to 255 characters. Legacy packages with 
  80-character prefixes must be rebuilt to take advantage of the
  longer prefix.

* There may be cases where conda identified a file as binary, but 
  it needs to have the build prefix replaced as if it were 
  text---no padding with null terminators. Such files can be 
  listed in build/has_prefix_files in ``meta.yaml``.
