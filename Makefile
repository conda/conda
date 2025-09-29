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


# Witness Integration Targets
# ============================

witness-help:
	@echo "Conda + Witness Integration Targets"
	@echo "===================================="
	@echo ""
	@echo "  make witness-deps     - Install dependencies for witness integration"
	@echo "  make witness-setup    - Download witness binary for current platform"
	@echo "  make witness-build    - Build conda package (for use with witness-run-action)"
	@echo "  make witness-verify   - Verify built package with conda verify"
	@echo "  make witness-test     - Run full witness integration test locally"
	@echo ""

witness-deps:
	pip install build wheel setuptools hatchling hatch-vcs
	pip install ruamel.yaml requests pycosat boltons platformdirs frozendict
	pip install jsonpatch packaging tqdm urllib3 charset-normalizer idna

witness-setup:
	python setup_witness.py --current-platform
	@echo "Witness binary downloaded:"
	@ls -la conda/witness/binaries/

witness-build:
	@echo "======================================"
	@echo "Building Conda Package with Witness"
	@echo "======================================"
	@echo "Python version: $$(python --version)"
	@echo "Current directory: $$(pwd)"
	@echo "Git commit: $$(git rev-parse HEAD 2>/dev/null || echo 'not a git repo')"
	@echo "Starting build..."
	python -m build --wheel --outdir dist/
	@echo ""
	@echo "Build artifacts:"
	ls -lh dist/
	@echo ""
	@echo "Checksums:"
	cd dist && sha256sum * | tee ../checksums.txt && cd ..
	@echo ""
	@echo "Build completed successfully!"

witness-policy:
	@cat > build-policy.yaml << 'EOF'
	expires: "2025-12-31T23:59:59Z"
	steps:
	  - name: conda-package-build
	    attestations:
	      - type: https://witness.dev/attestations/command-run/v0.1
	        regopolicies:
	          - name: exit-zero
	            module: |
	              package commandrun
	              default allow = false
	              allow { input.exitcode == 0 }
	      - type: https://witness.dev/attestations/product/v0.1
	        regopolicies:
	          - name: wheel-created
	            module: |
	              package product
	              default allow = false
	              allow {
	                some i
	                contains(input[i].name, ".whl")
	              }
	      - type: https://witness.dev/attestations/github/v0.1
	        regopolicies:
	          - name: github-build
	            module: |
	              package github
	              default allow = false
	              allow {
	                input.workflow != ""
	                input.repository == "testifysec/conda"
	              }
	      - type: https://witness.dev/attestations/environment/v0.1
	      - type: https://witness.dev/attestations/git/v0.1
	      - type: https://witness.dev/attestations/material/v0.1
	EOF
	@echo "Test policy generated: build-policy.yaml"

witness-sign-policy: witness-policy
	@echo "Generating test keys..."
	openssl genrsa -out policy-key.pem 2048
	openssl rsa -in policy-key.pem -pubout -out policy-key.pub
	@echo "Signing policy..."
	python -c "from conda.witness import get_witness_binary_path; import subprocess; witness = get_witness_binary_path(); subprocess.run([str(witness), 'sign', '--key', 'policy-key.pem', '--outfile', 'build-policy-signed.yaml', 'build-policy.yaml'], check=True)"
	@echo "✓ Policy signed"

witness-verify:
	@if [ -z "$$(ls dist/*.whl 2>/dev/null)" ]; then \
		echo "Error: No wheel file found in dist/. Run 'make witness-build' first."; \
		exit 1; \
	fi
	@export PYTHONPATH="$${PWD}:$${PYTHONPATH}"; \
	echo "======================================"; \
	echo "Verifying Conda Package with Witness"; \
	echo "======================================"; \
	WHEEL=$$(ls dist/*.whl | head -1); \
	echo "Package to verify: $$WHEEL"; \
	echo ""; \
	if [ -f conda-build.attestation.json ]; then \
		echo "Attestation summary:"; \
		cat conda-build.attestation.json | python -c "import json, sys; data = json.load(sys.stdin); print(f'  Type: {data.get(\"type\", \"unknown\")}')"; \
	fi; \
	echo ""; \
	echo "Running conda verify..."; \
	python -m conda.cli.main verify \
	  --artifactfile "$$WHEEL" \
	  --policy build-policy-signed.yaml \
	  --publickey policy-key.pub \
	  $$(test -f conda-build.attestation.json && echo "--attestations conda-build.attestation.json") \
	  --json > verify-result.json || true; \
	if [ -f verify-result.json ]; then \
		python -c "import json; result = json.load(open('verify-result.json')); print('✅ VERIFICATION SUCCESSFUL!' if result.get('verified') else '❌ Verification failed'); print(f'  Artifact: {result.get(\"artifact\")}'); print(f'  Policy: {result.get(\"policy\")}'); print(f'  Message: {result.get(\"message\")}')"; \
	fi

witness-clean:
	rm -rf dist/ build/ *.egg-info/
	rm -f *.json *.yaml *.pem *.pub *.txt
	rm -rf conda/witness/binaries/
	@echo "✓ Cleaned witness artifacts"

witness-test: witness-clean witness-deps witness-setup witness-build witness-sign-policy
	@echo ""
	@echo "======================================"
	@echo "Running Witness Integration Test"
	@echo "======================================"
	$(MAKE) witness-verify
	@echo ""
	@echo "✓ Witness integration test completed"

.PHONY: $(MAKECMDGOALS)
