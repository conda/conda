# Embedded Witness Binary Integration

## Overview

The `conda verify` command now includes embedded witness binaries, eliminating the need for users to separately install the witness CLI tool. This provides a seamless, out-of-the-box experience for supply chain verification.

## Architecture

### Binary Management

Witness binaries are embedded directly in the conda package under:
```
conda/witness/binaries/
├── witness_linux_x86_64
├── witness_linux_aarch64  
├── witness_darwin_x86_64
├── witness_darwin_arm64
└── witness_windows_amd64.exe
```

### Platform Detection

The system automatically detects the current platform and uses the appropriate binary:

1. **Primary**: Check for embedded binary matching current platform
2. **Fallback**: Check system PATH for existing witness installation
3. **Auto-download**: Optionally download binary if not found (development mode)

## Setup for Development

### Download Binary for Current Platform
```bash
python setup_witness.py --current-platform
```

### Download All Platform Binaries (for packaging)
```bash
python setup_witness.py --all-platforms
```

### Manual Download
```bash
python -m conda.witness.download_witness --platform linux_x86_64
```

## Testing

### Test Embedded Binary
```bash
python test_embedded_witness.py
```

### Run Integration Tests
```bash
./test-witness-integration.sh
```

## GitHub Actions Workflow

The workflow `.github/workflows/test-witness-verify-embedded.yml`:
- Tests on multiple platforms (Linux, macOS, Windows)
- Automatically downloads platform-specific binaries
- Verifies conda verify works without external witness installation
- Uses `witness-run-action` for attestation generation

## Packaging

### Including Binaries in Distribution

The `pyproject.toml` configuration ensures binaries are included:
```toml
[tool.hatch.build.targets.wheel]
include = [
  "conda/witness/binaries/witness_*",
]
```

### Binary Size Considerations

Each witness binary is approximately 60-70 MB. The full package with all platforms:
- Linux x86_64: ~65 MB
- Linux ARM64: ~62 MB  
- Darwin x86_64: ~68 MB
- Darwin ARM64: ~67 MB
- Windows x86_64: ~64 MB
- **Total**: ~326 MB (if all platforms included)

For size-conscious distributions, consider:
1. Platform-specific wheels (only include binary for target platform)
2. Separate witness-binaries package as optional dependency
3. On-demand download during first use

## Usage

Once installed, users can immediately use conda verify:

```bash
# No need to install witness separately!
conda verify --package numpy --policy policy.yaml --publickey key.pub

# The embedded binary is used transparently
conda verify --env --policy policy.yaml --attestations attestation.json
```

## Binary Updates

To update witness binaries to a new version:

1. Update `WITNESS_VERSION` in `conda/witness/download_witness.py`
2. Run `python setup_witness.py --all-platforms`
3. Update checksums in `WITNESS_CHECKSUMS` if verification is enabled
4. Test on all platforms
5. Commit the new binaries

## Security Considerations

### Binary Verification
- Downloaded binaries should be verified against checksums
- Consider GPG signature verification for releases
- Use official witness releases only

### Permissions
- Binaries are set as executable (755) on Unix systems
- Windows .exe files work without special permissions

### Trust Model
- Embedded binaries are trusted as part of conda package
- Users can override with system-installed witness if preferred
- Transparent fallback to system PATH maintains flexibility

## Advantages

✅ **Zero Dependencies**: Users don't need to install witness separately  
✅ **Cross-Platform**: Works on Linux, macOS, and Windows  
✅ **Offline Capable**: No network access required after installation  
✅ **Version Control**: Ensures compatible witness version  
✅ **Simplified CI/CD**: No need to install witness in workflows  

## Limitations

⚠️ **Package Size**: Adds ~65-70 MB per platform  
⚠️ **Binary Updates**: Requires conda update for new witness versions  
⚠️ **Architecture Support**: Limited to common architectures  

## Future Improvements

1. **Lazy Download**: Download binary on first use rather than at install
2. **Compression**: Use compressed binaries with runtime extraction
3. **Multi-Version Support**: Allow multiple witness versions
4. **Signature Verification**: Verify witness binary signatures
5. **WASM Alternative**: Consider WebAssembly for universal binary