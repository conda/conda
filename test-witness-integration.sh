#!/bin/bash
# Local test script for conda witness verify integration

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WITNESS_DIR="${SCRIPT_DIR}/.github/witness"
KEYS_DIR="${WITNESS_DIR}/keys"

echo "=========================================="
echo "Testing Conda Witness Verify Integration"
echo "=========================================="
echo ""

# Check if witness is installed
if ! command -v witness &> /dev/null; then
    echo "❌ Error: witness CLI is not installed"
    echo "Please install witness from: https://github.com/in-toto/witness/releases"
    exit 1
fi

echo "✓ Witness CLI found: $(which witness)"
witness version
echo ""

# Generate keys if they don't exist
if [ ! -f "${KEYS_DIR}/test-key.pub" ]; then
    echo "Generating test keys..."
    "${WITNESS_DIR}/generate-test-keys.sh"
    echo ""
fi

# Create a simple build artifact
echo "Creating test artifact..."
mkdir -p build-test
cat > build-test/manifest.json << EOF
{
  "name": "conda-test",
  "version": "1.0.0",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Add some dummy Python files
mkdir -p build-test/conda
echo "# Test module" > build-test/conda/__init__.py
echo "def verify(): return True" > build-test/conda/verify_test.py

# Create tarball
tar -czf conda-test.tar.gz -C build-test .
echo "✓ Created test artifact: conda-test.tar.gz"
echo ""

# Create a simple policy
echo "Creating test policy..."
cat > test-policy.yaml << EOF
expires: "2030-01-01T00:00:00Z"
steps:
  - name: test-step
    attestations:
      - type: https://witness.dev/attestations/command-run/v0.1
      - type: https://witness.dev/attestations/material/v0.1
    functionaries:
      - type: publickey
        publickeyid: "test-key"
publickeys:
  test-key:
    keyid: "test-key"
    key: |
$(sed 's/^/      /' "${KEYS_DIR}/test-key.pub")
EOF
echo "✓ Created test policy"
echo ""

# Sign the policy
echo "Signing the policy..."
witness sign \
    --key "${KEYS_DIR}/policy-key.pem" \
    --outfile test-policy-signed.yaml \
    test-policy.yaml
echo "✓ Policy signed"
echo ""

# Create attestation with witness
echo "Creating attestation..."
witness run \
    --key "${KEYS_DIR}/test-key.pem" \
    --step test-step \
    --outfile test-attestation.json \
    --attestors material \
    --attestors command-run \
    --command "echo 'Test build'" \
    -- echo "Building conda..."
echo "✓ Attestation created"
echo ""

# Test conda verify command
echo "Testing conda verify..."
echo "========================"
echo ""

# Set PYTHONPATH to use local conda
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Test 1: Basic verification with artifact file
echo "Test 1: Verifying artifact file..."
python3 -m conda.cli.main verify \
    --artifactfile conda-test.tar.gz \
    --policy test-policy-signed.yaml \
    --publickey "${KEYS_DIR}/policy-key.pub" \
    --attestations test-attestation.json \
    && echo "✓ Test 1 passed: Artifact verification successful" \
    || echo "✗ Test 1 failed: Artifact verification failed"
echo ""

# Test 2: Directory verification
echo "Test 2: Verifying directory..."
python3 -m conda.cli.main verify \
    --directory-path build-test \
    --policy test-policy-signed.yaml \
    --publickey "${KEYS_DIR}/policy-key.pub" \
    --attestations test-attestation.json \
    && echo "✓ Test 2 passed: Directory verification successful" \
    || echo "✗ Test 2 failed: Directory verification failed"
echo ""

# Test 3: JSON output
echo "Test 3: Testing JSON output..."
python3 -m conda.cli.main verify \
    --artifactfile conda-test.tar.gz \
    --policy test-policy-signed.yaml \
    --publickey "${KEYS_DIR}/policy-key.pub" \
    --attestations test-attestation.json \
    --json > verify-output.json 2>/dev/null \
    && echo "✓ Test 3 passed: JSON output generated" \
    || echo "✗ Test 3 failed: JSON output failed"

if [ -f verify-output.json ]; then
    echo "JSON output preview:"
    cat verify-output.json | python3 -m json.tool | head -20
fi
echo ""

# Test 4: Help output
echo "Test 4: Testing help output..."
python3 -m conda.cli.main verify --help > /dev/null 2>&1 \
    && echo "✓ Test 4 passed: Help output works" \
    || echo "✗ Test 4 failed: Help output failed"
echo ""

# Test 5: Error handling - missing policy
echo "Test 5: Testing error handling (missing policy)..."
python3 -m conda.cli.main verify \
    --artifactfile conda-test.tar.gz \
    --policy non-existent-policy.yaml 2>&1 | grep -qi "error\|not found" \
    && echo "✓ Test 5 passed: Error correctly reported for missing policy" \
    || echo "✗ Test 5 failed: Error handling issue"
echo ""

# Clean up
echo "Cleaning up test artifacts..."
rm -rf build-test
rm -f conda-test.tar.gz
rm -f test-policy.yaml
rm -f test-policy-signed.yaml
rm -f test-attestation.json
rm -f verify-output.json

echo ""
echo "=========================================="
echo "✅ Integration tests completed!"
echo "=========================================="
echo ""
echo "To run in GitHub Actions, push the changes and the workflow will trigger."
echo "Check: .github/workflows/test-witness-verify.yml"