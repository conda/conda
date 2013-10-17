from __future__ import print_function, division, absolute_import

def install_from_pypi(args, parser):
    print("Conda package not available, attempting to create one from pypi...")
    import pdb
    pdb.set_trace()
    try:
        print("Creating recipe...")
        # run conda skeleton pypi <package-name> --no-prompt --output-dir root-prefix/conda-recipes
        print("Building recipe...")
        # run conda build root-prefix/conda-recipes/package-name --no-binstar-upload
        print("Installing conda package...")
        # run conda install root-prefix/conda-bld/<platform>/<package-name><...>.tar.bz2
    except Exception as err:
        print(err)
        raise RuntimeError("Could not install package from pypi")



