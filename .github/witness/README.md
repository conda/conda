# Witness Integration Testing for Conda

This directory contains test resources for the `conda verify` command integration with in-toto/witness.

## Directory Structure

```
.github/witness/
├── README.md                  # This file
├── generate-test-keys.sh      # Script to generate test keys
├── policy-template.yaml       # Template for witness policies
├── example-policy.yaml        # Simple example policy
└── keys/                      # Test keys directory
    ├── .gitignore            # Prevents committing private keys
    ├── policy-key.pub        # Public key for policy verification
    ├── test-key.pub          # Public key for test attestations
    ├── build-key.pub         # Public key for build attestations
    └── functionary-key.pub   # Public key for functionary identity
```

## GitHub Actions Workflow

The workflow `.github/workflows/test-witness-verify.yml` tests the conda verify integration:

### Workflow Steps

1. **Setup**: Install Python, witness CLI, and conda dependencies
2. **Key Generation**: Generate test RSA key pairs for signing
3. **Build with Attestation**: Use witness-run-action to create attestations
4. **Policy Creation**: Generate and sign a witness policy
5. **Verification Tests**: Test various conda verify scenarios
6. **Negative Tests**: Ensure proper error handling

### Trigger Conditions

The workflow runs on:
- Push to `feat/conda-witness` or `main` branches
- Pull requests affecting witness-related files
- Manual trigger via workflow_dispatch

## Local Testing

### Prerequisites

1. Install witness CLI:
```bash
# macOS/Linux
curl -L https://github.com/in-toto/witness/releases/latest/download/witness_$(uname -s)_$(uname -m).tar.gz -o witness.tar.gz
tar -xzf witness.tar.gz
sudo mv witness /usr/local/bin/
```

2. Install Python dependencies:
```bash
pip install ruamel.yaml requests pycosat boltons platformdirs frozendict
```

### Running Tests

1. Generate test keys:
```bash
.github/witness/generate-test-keys.sh
```

2. Run the integration test:
```bash
./test-witness-integration.sh
```

## Key Management

### Test Keys

The `generate-test-keys.sh` script creates several key pairs:
- **policy-key**: For signing witness policies
- **test-key**: For test attestations
- **build-key**: For build process attestations
- **functionary-key**: For functionary identity
- **ed25519-key**: Alternative Ed25519 key pair

### Security Notes

- Private keys (*.pem) are automatically gitignored
- Only public keys (*.pub) should be committed
- These are TEST keys only - never use in production
- Generate new keys for actual deployments

## Policy Examples

### Simple Policy (example-policy.yaml)

Basic policy requiring command-run and environment attestations:
```yaml
expires: "2030-01-01T00:00:00Z"
steps:
  - name: build
    attestations:
      - type: https://witness.dev/attestations/command-run/v0.1
      - type: https://witness.dev/attestations/environment/v0.1
    functionaries:
      - type: publickey
        publickeyid: "test-functionary"
```

### Advanced Policy (policy-template.yaml)

Comprehensive policy with:
- Multiple attestation types
- Rego policies for validation
- Git and GitHub attestations
- Multiple build steps

## Troubleshooting

### Common Issues

1. **Witness not found**: Install witness CLI as shown in prerequisites
2. **Key permission errors**: Ensure private keys have 600 permissions
3. **Policy validation fails**: Check key IDs match between policy and attestations
4. **Python import errors**: Install all required conda dependencies

### Debugging

Enable debug output:
```bash
export CONDA_DEBUG=1
witness verify --log-level debug ...
```

View attestation contents:
```bash
cat attestation.json | jq '.'
```

Verify policy signature:
```bash
witness verify-signature --key policy-key.pub policy-signed.yaml
```

## Resources

- [Witness Documentation](https://witness.dev)
- [Witness GitHub](https://github.com/in-toto/witness)
- [in-toto Specification](https://in-toto.io)
- [Conda Verify Documentation](../../WITNESS_INTEGRATION.md)