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


.PHONY : clean clean-all anaconda-submit
