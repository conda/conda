PYTEST_EXE ?= $(shell which py.test)
PYTHON_EXE ?= $(shell sed 's/^\#!//' $(PYTEST_EXE) | head -1 | sed "s|$HOME|~|")
PYTHON_MAJOR_VERSION := $(shell $(PYTHON_EXE) -c "import sys; print(sys.version_info[0])")
TEST_PLATFORM := $(shell $(PYTHON_EXE) -c "import sys; print('win' if sys.platform.startswith('win') else 'unix')")
PYTHONHASHSEED := $(shell python -c "import random as r; print(r.randint(0,4294967296))")


PYTEST_VARS := PYTHONHASHSEED=$(PYTHONHASHSEED) PYTHON_MAJOR_VERSION=$(PYTHON_MAJOR_VERSION) TEST_PLATFORM=$(TEST_PLATFORM)
PYTEST := $(PYTEST_VARS) $(PYTEST_EXE)

ADD_COV := --cov-report xml --cov-report term-missing --cov-append --cov conda


clean:
	@find . -name \*.py[cod] -delete
	@find . -name __pycache__ -delete
	@rm -rf *.egg-info* .cache build
	@rm -f .coverage .coverage.* junit.xml tmpfile.rc conda/.version tempfile.rc coverage.xml
	@rm -rf auxlib bin conda/progressbar


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


pytest-version:
	$(PYTEST) --version


conda-version:
	$(PYTHON_EXE) utils/setup-testing.py --version


smoketest:
	$(PYTEST) tests/test_create.py -k test_create_install_update_remove


unit: clean
	$(PYTEST) $(ADD_COV) -m "not integration and not installed"


integration: clean pytest-version
	$(PYTEST) $(ADD_COV) -m "not installed"


test-installed:
	$(PYTEST) $(ADD_COV) -m "installed" --shell=bash --shell=zsh


.PHONY : clean clean-all anaconda-submit anaconda-submit-upload auxlib boltons toolz \
         pytest-version smoketest unit integration test-installed
