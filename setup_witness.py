#!/usr/bin/env python3
"""Setup script to prepare witness binaries for conda packaging."""

import sys
from pathlib import Path

# Add conda to path
sys.path.insert(0, str(Path(__file__).parent))

from conda.witness.download_witness import download_all_platforms, download_witness_binary


def main():
    """Download witness binaries for packaging."""
    print("="*60)
    print("Setting up witness binaries for conda")
    print("="*60)
    
    import argparse
    parser = argparse.ArgumentParser(
        description="Setup witness binaries for conda packaging"
    )
    parser.add_argument(
        "--current-platform",
        action="store_true",
        help="Download only for current platform (for development)"
    )
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Download for all supported platforms (for packaging)"
    )
    
    args = parser.parse_args()
    
    binaries_dir = Path(__file__).parent / "conda" / "witness" / "binaries"
    
    if args.all_platforms:
        print("\nDownloading witness binaries for all platforms...")
        downloaded, failed = download_all_platforms(binaries_dir)
        
        if failed:
            print(f"\nWarning: Failed to download for {len(failed)} platform(s)")
            print("The package will work on platforms where binaries were successfully downloaded")
        
        if downloaded:
            print(f"\nSuccessfully prepared {len(downloaded)} platform binaries")
            print("\nTo include in conda package, ensure the binaries are included in:")
            print("  - meta.yaml (for conda-build)")
            print("  - pyproject.toml package-data (for pip)")
            print("  - MANIFEST.in (for sdist)")
    
    else:
        # Default: download for current platform only
        print("\nDownloading witness binary for current platform...")
        result = download_witness_binary(None, binaries_dir)
        
        if result:
            print(f"\nSuccess! Witness binary downloaded to: {result}")
            print("\nYou can now use 'conda verify' command")
            
            # Test import
            try:
                from conda.witness import check_witness_installed
                if check_witness_installed():
                    print("✓ Witness integration is ready")
                else:
                    print("⚠ Witness binary downloaded but not detected")
            except ImportError as e:
                print(f"⚠ Could not import witness module: {e}")
        else:
            print("\n✗ Failed to download witness binary")
            print("You can manually download from: https://github.com/in-toto/witness/releases")
            sys.exit(1)


if __name__ == "__main__":
    main()