clean:
	find . -name \*.py[cod] -delete
	find . -name __pycache__ -delete
	rm -rf *.egg-info* .cache build
	rm -f .coverage junit.xml tmpfile.rc conda/.version


# VERSION=0.0.40 make requests
auxlib:
	git clone https://github.com/kalefranz/auxlib.git --single-branch --branch $(VERSION) \
	    && rm -rf conda/_vendor/auxlib \
	    && mv auxlib/auxlib conda/_vendor/ \
	    && rm -rf auxlib

clean-all: clean
	rm -rf dist env ve


# REQUESTS_VERSION=v2.10.0 make requests
requests:
	git clone https://github.com/kennethreitz/requests.git --single-branch --branch $(REQUESTS_VERSION) \
 	    && rm -rf conda/_vendor/requests \
 	    && mv requests/requests conda/_vendor/ \
 	    && rm -rf requests


anaconda-submit-test: clean-all
	anaconda build submit . --queue conda-team/build_recipes --test-only


anaconda-submit-upload: clean-all
	anaconda build submit . --queue conda-team/build_recipes --label stage


.PHONY : clean clean-all requests anaconda-submit anaconda-submit-upload
