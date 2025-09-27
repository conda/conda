# Conda Verify Command - in-toto/witness Integration

## Overview

The `conda verify` command integrates the in-toto/witness attestation verification tool directly into the conda CLI, allowing users to verify the integrity and provenance of conda packages and environments using attestations and policies.

## Prerequisites

- The `witness` CLI tool must be installed and available in your system PATH
- Download from: https://github.com/in-toto/witness/releases
- Or install via: `go install github.com/in-toto/witness@latest`

## Command Usage

### Basic Syntax

```bash
conda verify [OPTIONS] --policy <POLICY_FILE>
```

### Verification Targets

You must specify one of the following targets:

- `--package PACKAGE` - Verify a specific conda package
- `--env` - Verify the current conda environment
- `--prefix PATH` - Verify a specific conda environment by path
- `--artifactfile PATH` - Verify a specific artifact file
- `--directory-path PATH` - Verify a directory

### Required Arguments

- `-p, --policy PATH` - Path to the in-toto policy file to verify against

### Optional Arguments

#### Authentication
- `-k, --publickey PATH` - Path to the policy signer's public key
- `--policy-ca-roots PATH` - CA root certificates for x.509 signed policies
- `--policy-ca-intermediates PATH` - CA intermediate certificates

#### Attestations
- `-a, --attestations PATH` - Attestation files (can be specified multiple times)
- `-s, --subjects SUBJECT` - Additional subjects to lookup attestations

#### Archivista Integration
- `--enable-archivista` - Use Archivista to retrieve attestations
- `--archivista-server URL` - Archivista server URL (default: https://archivista.testifysec.io)
- `--archivista-token TOKEN` - Authentication token for Archivista

#### Additional Options
- `--witness-options "OPTIONS"` - Pass additional options directly to witness
- `--json` - Output results in JSON format

## Examples

### Verify a Package

```bash
# Basic package verification with policy and public key
conda verify --package numpy --policy policy.yaml --publickey key.pub

# Package verification with local attestation files
conda verify --package pandas --policy policy.yaml \
  --attestations attestation1.json \
  --attestations attestation2.json

# Package verification using Archivista
conda verify --package scipy --policy policy.yaml \
  --enable-archivista \
  --archivista-server https://archivista.example.com
```

### Verify Current Environment

```bash
# Verify the currently activated conda environment
conda verify --env --policy policy.yaml --publickey key.pub

# Verify with x.509 signed policy
conda verify --env --policy policy.yaml \
  --policy-ca-roots ca-root.crt \
  --policy-ca-intermediates ca-intermediate.crt
```

### Verify Specific Environment

```bash
# Verify a specific environment by path
conda verify --prefix /path/to/conda/env --policy policy.yaml

# Verify with additional subjects
conda verify --prefix ~/miniconda3/envs/myenv --policy policy.yaml \
  --subjects "pkg:conda/numpy@1.21.0" \
  --subjects "pkg:conda/pandas@1.3.0"
```

### Direct Artifact Verification

```bash
# Verify a specific package file
conda verify --artifactfile numpy-1.21.0-py39.tar.bz2 \
  --policy policy.yaml --publickey key.pub

# Verify a directory
conda verify --directory-path /path/to/extracted/package \
  --policy policy.yaml
```

## How It Works

1. **Target Resolution**: The command first resolves the verification target:
   - For packages: Searches conda package cache directories
   - For environments: Validates conda environment structure
   - For direct paths: Verifies file/directory existence

2. **Witness Invocation**: Constructs and executes a witness verify command with:
   - Resolved artifact path
   - Policy and authentication parameters
   - Attestation sources (local files or Archivista)

3. **Result Processing**: Returns verification status:
   - Exit code 0: Verification successful
   - Non-zero exit code: Verification failed
   - JSON output available with `--json` flag

## Implementation Details

### File Structure

- `conda/cli/main_verify.py` - Main command implementation
- `conda/witness/__init__.py` - Witness integration utilities
- `conda/cli/conda_argparse.py` - Command registration

### Key Functions

- `check_witness_installed()` - Verifies witness CLI availability
- `find_package_artifact()` - Locates conda packages in cache
- `resolve_environment_path()` - Validates environment paths
- `run_witness_verify()` - Executes witness verification

## Error Handling

The command will fail with appropriate error messages for:
- Missing witness CLI tool
- Package not found in conda cache
- Invalid environment path
- Missing or invalid policy file
- Verification failures

## Security Considerations

- Always verify the authenticity of policy files before use
- Store public keys and CA certificates securely
- Use Archivista with proper authentication when available
- Regularly update attestations for installed packages

## Future Enhancements

Potential improvements for future versions:
- Automatic policy discovery based on package metadata
- Integration with conda's existing trust infrastructure
- Batch verification of multiple packages
- Caching of verification results
- Direct Go library integration for better performance