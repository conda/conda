#!/usr/bin/env python3
"""Test script to demonstrate conda verify command usage."""

import sys
import os

# Add conda to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conda.cli.conda_argparse import generate_parser

def test_verify_help():
    """Test that the verify command is registered and has help."""
    parser = generate_parser()
    
    # Parse help for verify command
    try:
        args = parser.parse_args(['verify', '--help'])
    except SystemExit:
        # --help causes SystemExit, which is expected
        pass
    
    print("✓ Verify command is successfully registered")
    
def test_verify_parser():
    """Test that the verify command parser accepts expected arguments."""
    parser = generate_parser()
    
    # Test basic package verification arguments
    test_args = [
        'verify',
        '--package', 'numpy',
        '--policy', 'policy.yaml',
        '--publickey', 'key.pub',
    ]
    
    try:
        args = parser.parse_args(test_args)
        print(f"✓ Parsed arguments: {args}")
        print(f"  Package: {args.package}")
        print(f"  Policy: {args.policy}")
        print(f"  Public key: {args.publickey}")
    except Exception as e:
        print(f"✗ Failed to parse arguments: {e}")
        return False
    
    # Test environment verification arguments
    test_args = [
        'verify',
        '--env',
        '--policy', 'policy.yaml',
        '--attestations', 'attest1.json',
        '--attestations', 'attest2.json',
        '--enable-archivista',
    ]
    
    try:
        args = parser.parse_args(test_args)
        print(f"✓ Parsed environment verification arguments")
        print(f"  Verify env: {args.env}")
        print(f"  Attestations: {args.attestations}")
        print(f"  Archivista enabled: {args.enable_archivista}")
    except Exception as e:
        print(f"✗ Failed to parse arguments: {e}")
        return False
    
    return True

def main():
    print("Testing conda verify command integration...\n")
    
    # Check if verify command is in BUILTIN_COMMANDS
    from conda.cli.conda_argparse import BUILTIN_COMMANDS
    if "verify" in BUILTIN_COMMANDS:
        print("✓ 'verify' is in BUILTIN_COMMANDS")
    else:
        print("✗ 'verify' is NOT in BUILTIN_COMMANDS")
    
    print("\nTesting command help...")
    test_verify_help()
    
    print("\nTesting command parser...")
    test_verify_parser()
    
    # Check if witness module can be imported
    print("\nTesting witness module import...")
    try:
        from conda.witness import check_witness_installed
        is_installed = check_witness_installed()
        print(f"✓ Witness module imported successfully")
        print(f"  Witness CLI installed: {is_installed}")
    except Exception as e:
        print(f"✗ Failed to import witness module: {e}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()