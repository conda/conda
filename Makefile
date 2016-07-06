clean:
	find . -name \*.py[cod] -delete
	find . -name __pycache__ -delete
	rm -rf *.egg-info* .cache build
	rm -f .coverage junit.xml tmpfile.rc conda/.version


clean-all: clean
	rm -rf dist env ve


anaconda-submit-test: clean-all
	anaconda build submit . --queue conda-team/build_recipes --test-only


anaconda-submit-upload: clean-all
	anaconda build submit . --queue conda-team/build_recipes --label stage


# VERSION=0.0.40 make auxlib
auxlib:
	git clone https://github.com/kalefranz/auxlib.git --single-branch --branch $(VERSION) \
	    && rm -rf conda/_vendor/auxlib \
	    && mv auxlib/auxlib conda/_vendor/ \
	    && rm -rf auxlib


# VERSION=v2.10.0 make requests
requests:
	git clone https://github.com/kennethreitz/requests.git --single-branch --branch $(VERSION) \
 	    && rm -rf conda/_vendor/requests \
 	    && mv requests/requests conda/_vendor/ \
 	    && rm -rf requests


# VERSION=0.8.0 make toolz
toolz:
	git clone https://github.com/pytoolz/toolz.git --single-branch --branch $(VERSION) \
 	    && rm -rf conda/_vendor/toolz \
 	    && mv toolz/toolz conda/_vendor/ \
 	    && rm -rf toolz


.PHONY : clean clean-all anaconda-submit anaconda-submit-upload auxlib requests toolz
