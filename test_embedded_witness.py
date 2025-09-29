#!/usr/bin/env python3
"""Test script for embedded witness binary integration."""

import sys
import subprocess
from pathlib import Path

def test_embedded_witness():
    """Test that the embedded witness binary works."""
    
    print("Testing Embedded Witness Binary Integration")
    print("=" * 50)
    
    # Test 1: Check if module imports correctly
    try:
        from conda.witness import check_witness_installed, get_witness_binary_path
        print("✓ Module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import module: {e}")
        return False
    
    # Test 2: Check if witness binary can be found
    witness_path = get_witness_binary_path()
    if witness_path:
        print(f"✓ Witness binary found: {witness_path}")
    else:
        print("✗ Witness binary not found")
        print("\nTo fix this, run: python setup_witness.py --current-platform")
        return False
    
    # Test 3: Check if binary is executable
    try:
        result = subprocess.run(
            [str(witness_path), "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ Witness binary is executable")
            print(f"  Version output: {result.stdout.strip()}")
        else:
            print(f"✗ Witness binary failed to execute")
            print(f"  Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Failed to execute witness binary: {e}")
        return False
    
    # Test 4: Check conda verify command registration
    try:
        from conda.cli.conda_argparse import BUILTIN_COMMANDS
        if "verify" in BUILTIN_COMMANDS:
            print("✓ 'verify' command is registered in conda")
        else:
            print("✗ 'verify' command not found in BUILTIN_COMMANDS")
            return False
    except ImportError as e:
        print(f"⚠ Could not check command registration: {e}")
    
    # Test 5: Test the check_witness_installed function
    if check_witness_installed():
        print("✓ check_witness_installed() returns True")
    else:
        print("✗ check_witness_installed() returns False")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! Embedded witness is working.")
    print("\nYou can now use 'conda verify' without installing witness separately!")
    print("\nExample usage:")
    print("  python -m conda.cli.main verify --help")
    print("  conda verify --package numpy --policy policy.yaml --publickey key.pub")
    
    return True

def main():
    """Main entry point."""
    # Check if binaries directory exists
    binaries_dir = Path(__file__).parent / "conda" / "witness" / "binaries"
    
    if not binaries_dir.exists():
        binaries_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created binaries directory: {binaries_dir}")
    
    # List existing binaries
    existing = list(binaries_dir.glob("witness_*"))
    if existing:
        print(f"Found {len(existing)} existing witness binaries:")
        for binary in existing:
            size_mb = binary.stat().st_size / (1024 * 1024)
            print(f"  - {binary.name} ({size_mb:.2f} MB)")
    else:
        print("No witness binaries found.")
        print("\nTo download witness binary for your platform, run:")
        print("  python setup_witness.py --current-platform")
        print("\nTo download for all platforms (for packaging), run:")
        print("  python setup_witness.py --all-platforms")
    
    print()
    
    # Run tests
    success = test_embedded_witness()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()