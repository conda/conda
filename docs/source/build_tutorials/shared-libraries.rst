r conda packages
================

[github.com/conda/conda](github.com/conda/conda)
Study relationship to RPATH and post.py

https://github.com/conda/conda-build/issues/45

https://github.com/conda/conda-build/issues/83

Questions
---------

1. Take a look at https://github.com/tpn/enversion-dist/blob/master/conda/apr-util-1.5.3/meta.yaml

2. Note the requirements->build/run sections

3. What exactly is being specified there?

4. What are the implications of having '- apr' as a runtime requirement?

5. Let's take a look at the apr recipe:
https://github.com/tpn/enversion-dist/tree/master/conda/apr-1.5.0

6. Using the paths referenced in the meta.yaml, download the source tarball
somewhere, then replicate the build steps in build.sh... but switch out $PREFIX
for something like ~/tmp/fuzzybear/apr.  (We're about to grep for fuzzybear,
hence the uniqueness of it.  There probably isn't anything else in the apr
source tree that has the word fuzzybear in it.)

7. cd ~/tmp/fuzzybear

8. find . -type f | xargs fgrep -ni fuzzybear

9. Hopefully there are so apr*.so-type files that match when you run this, heh.

10. Find one of the .so files and run ldd on them... note the list of libraries coming up.

11. Try running patchelf/chrpath to display any RPATHs set on those .so libraries.

12. Now... cd into the ~/src/enversion-dist/conda/apr-1.5.0 directory and do
conda build --no-test . (I think --no-test is needed to stop it from wiping
away the temp build directory which we need in the next step.)

13. cd into the temp build work directory... I can't remember if it's
~/anaconda/conda-bld/work/apr-1.5.0 or ~/anaconda/envs/_build.  Oh, wait, so,
the source gets extracted into the former, then when you do conda build... the
value of $PREFIX basically expands to ~/anaconda/envs/_build.

a. (That is, conda sets the environment variable PREFIX to
~/anaconda/envs/_build before it invokes the build.sh script.)

14. (Once the build completes (that is, build.sh returns with a 0 status code
(0 = no error)), conda build looks in $PREFIX and runs the "post-build" stuff.
Take a look at conda-build project's build.py and post.py for more info...
search for patchelf and backtrack from there.  It basically scans ELF headers
looking for dynamic libraries (.so files) and then *sets* the RPATH to a
location that's relative to $PREFIX/lib.)

a. (That last part is too simplistic -- it's been working fine to date, but it
assumes the library only installs stuff into $PREFIX/lib and doesn't have any
dependent libraries elsewhere.  That assumption doesn't hold with other
non-Python packages like R + R packages.  <-- which is the crux of the
outstanding R issues.)

15. So basically, the idea is to compare the .so files that conda ends up
preparing and putting into the .tar.bz2 versus the .so file that you'd get if
you just did a `./configure && make && make install`.

16. The difference is simply that RPATH tweak such that the .so is no longer
dependent upon the path it was installed into during `make install`.

