clean:
	find . -name \*.py[cod] -delete
	find . -name __pycache__ -delete
	rm -rf *.egg-info* .cache build
	rm -f .coverage junit.xml tmpfile.rc conda/.version tempfile.rc coverage.xml
	rm -rf auxlib bin conda/progressbar
	rm -rf conda-forge\:\: file\: https\: local\:\: r\:\: var


clean-all: clean
	rm -rf dist env ve


anaconda-submit-test: clean-all
	anaconda build submit . --queue conda-team/build_recipes --test-only


anaconda-submit-upload: clean-all
	anaconda build submit . --queue conda-team/build_recipes --label stage


# VERSION=0.0.41 make auxlib
auxlib:
	git clone https://github.com/kalefranz/auxlib.git --single-branch --branch $(VERSION) \
	    && rm -rf conda/_vendor/auxlib \
	    && mv auxlib/auxlib conda/_vendor/ \
	    && rm -rf auxlib


# VERSION=16.4.1 make boltons
boltons:
	git clone https://github.com/mahmoud/boltons.git --single-branch --branch $(VERSION) \
	    && rm -rf conda/_vendor/boltons \
	    && mv boltons/boltons conda/_vendor/ \
	    && rm -rf boltons


# VERSION=0.8.0 make toolz
toolz:
	git clone https://github.com/pytoolz/toolz.git --single-branch --branch $(VERSION) \
	    && rm -rf conda/_vendor/toolz \
	    && mv toolz/toolz conda/_vendor/ \
	    && rm -rf toolz
	rm -rf conda/_vendor/toolz/curried conda/_vendor/toolz/sandbox conda/_vendor/toolz/tests


.PHONY : clean clean-all anaconda-submit anaconda-submit-upload auxlib boltons toolz
