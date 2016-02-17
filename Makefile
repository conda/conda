REQUESTS_VERSION := v2.9.1

_vendor:
	@mkdir -p conda/_vendor
	@touch conda/_vendor/__init__.py


requests: _vendor
	git clone https://github.com/kennethreitz/requests.git --branch $(REQUESTS_VERSION) \
	    && rm -rf conda/_vendor/requests \
	    && mv requests/requests conda/_vendor/ \
	    && rm -rf requests
