SHELL := /bin/bash -o pipefail -o errexit

clean:
	find . -name \*.py[cod] -delete
	find . -name __pycache__ -delete
	rm -rf .cache build
	rm -f .coverage .coverage.* junit.xml tmpfile.rc tempfile.rc coverage.xml
	rm -rf auxlib bin conda/progressbar
	rm -rf conda-build conda_build_test_recipe record.txt
	rm -rf .pytest_cache


clean-all:
	@echo Deleting everything not belonging to the git repo:
	git clean -fdx


anaconda-submit-test: clean-all
	anaconda build submit . --queue conda-team/build_recipes --test-only


anaconda-submit-upload: clean-all
	anaconda build submit . --queue conda-team/build_recipes --label stage


pytest-version:
	pytest --version


smoketest:
	pytest tests/test_create.py -k test_create_install_update_remove


unit:
	pytest -m "not integration and not installed"


integration: clean pytest-version
	pytest -m "integration and not installed"


test-installed:
	pytest -m "installed" --shell=bash --shell=zsh


html:
	cd docs && make html


.PHONY: $(MAKECMDGOALS)
