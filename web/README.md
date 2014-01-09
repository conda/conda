You will need to

    pip install sphinxjp.themes.basicstrap

Unfortunately, there is not a working conda package for this yet, because of
https://github.com/pydata/conda/issues/488.


Use

    make html

to build the docs

Use

    make test

after you have built the docs to upload it to the test site, and

    make live

to upload it to the conda.pydata.org site. You will need ssh access to
pydata.org to do these (obviously).
