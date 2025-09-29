#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Download witness binaries for bundling with conda."""

import hashlib
import os
import platform
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

# Witness release version to download
WITNESS_VERSION = "v0.9.2"  # Update this to latest stable version

# Platform mappings for witness releases
# Note: witness uses the pattern witness_VERSION_OS_ARCH.tar.gz
WITNESS_PLATFORMS = {
    ("Linux", "x86_64"): "witness_{version}_linux_amd64.tar.gz",
    ("Linux", "aarch64"): "witness_{version}_linux_arm64.tar.gz",
    ("Darwin", "x86_64"): "witness_{version}_darwin_amd64.tar.gz",
    ("Darwin", "arm64"): "witness_{version}_darwin_arm64.tar.gz",
    ("Windows", "AMD64"): "witness_{version}_windows_amd64.tar.gz",
}

# Expected checksums for each platform (update these for each version)
# These would need to be updated for each release
WITNESS_CHECKSUMS = {
    "witness_0.9.2_linux_amd64.tar.gz": None,  # Add actual checksums
    "witness_0.9.2_linux_arm64.tar.gz": None,
    "witness_0.9.2_darwin_amd64.tar.gz": None,
    "witness_0.9.2_darwin_arm64.tar.gz": None,
    "witness_0.9.2_windows_amd64.tar.gz": None,
}


def get_platform_info():
    """Get current platform information."""
    system = platform.system()
    machine = platform.machine()
    
    # Normalize machine architecture
    if machine in ("AMD64", "x86_64"):
        machine = "x86_64"
    elif machine in ("aarch64", "arm64"):
        machine = "aarch64" if system == "Linux" else "arm64"
    
    return system, machine


def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"Downloading: {url}")
    print(f"Destination: {dest_path}")
    
    with urllib.request.urlopen(url) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 8192
        
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"Progress: {progress:.1f}%", end="\r")
    
    print("\nDownload complete!")


def verify_checksum(file_path, expected_checksum):
    """Verify the SHA256 checksum of a file."""
    if expected_checksum is None:
        print("Warning: No checksum verification (checksum not provided)")
        return True
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    actual_checksum = sha256_hash.hexdigest()
    if actual_checksum != expected_checksum:
        print(f"Checksum mismatch!")
        print(f"Expected: {expected_checksum}")
        print(f"Actual: {actual_checksum}")
        return False
    
    print("Checksum verified successfully")
    return True


def extract_witness_binary(archive_path, dest_dir):
    """Extract witness binary from tar.gz archive."""
    print(f"Extracting witness binary from {archive_path}")
    
    with tarfile.open(archive_path, "r:gz") as tar:
        # Find the witness binary in the archive
        for member in tar.getmembers():
            if member.name in ("witness", "witness.exe"):
                print(f"Found binary: {member.name}")
                tar.extract(member, dest_dir)
                
                # Get the extracted binary path
                binary_path = Path(dest_dir) / member.name
                
                # Make it executable on Unix-like systems
                if platform.system() != "Windows":
                    binary_path.chmod(0o755)
                
                return binary_path
    
    raise FileNotFoundError("Witness binary not found in archive")


def download_witness_binary(platform_key=None, dest_dir=None):
    """Download witness binary for specified or current platform."""
    if dest_dir is None:
        # Default to binaries directory relative to this script
        dest_dir = Path(__file__).parent / "binaries"
    else:
        dest_dir = Path(dest_dir)
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    if platform_key is None:
        system, machine = get_platform_info()
        platform_key = (system, machine)
    
    if platform_key not in WITNESS_PLATFORMS:
        print(f"Error: Unsupported platform: {platform_key}")
        print(f"Supported platforms: {list(WITNESS_PLATFORMS.keys())}")
        return None
    
    # Format the archive name with version number (e.g., witness_0.9.2_darwin_arm64.tar.gz)
    version_num = WITNESS_VERSION.lstrip('v')  # Remove 'v' prefix for filename
    archive_name_template = WITNESS_PLATFORMS[platform_key]
    archive_name = archive_name_template.format(version=version_num)
    
    base_url = f"https://github.com/in-toto/witness/releases/download/{WITNESS_VERSION}"
    download_url = f"{base_url}/{archive_name}"
    
    # Download to temp file
    temp_archive = dest_dir / f"temp_{archive_name}"
    
    try:
        # Download the archive
        download_file(download_url, temp_archive)
        
        # Verify checksum if available
        expected_checksum = WITNESS_CHECKSUMS.get(archive_name)
        if not verify_checksum(temp_archive, expected_checksum):
            print("Error: Checksum verification failed")
            return None
        
        # Extract the binary
        binary_path = extract_witness_binary(temp_archive, dest_dir)
        
        # Rename to platform-specific name
        platform_suffix = f"{platform_key[0].lower()}_{platform_key[1]}"
        final_name = f"witness_{platform_suffix}"
        if platform_key[0] == "Windows":
            final_name += ".exe"
        
        final_path = dest_dir / final_name
        if final_path.exists():
            final_path.unlink()
        
        binary_path.rename(final_path)
        
        print(f"Successfully downloaded witness binary: {final_path}")
        return final_path
        
    finally:
        # Clean up temp file
        if temp_archive.exists():
            temp_archive.unlink()


def download_all_platforms(dest_dir=None):
    """Download witness binaries for all supported platforms."""
    if dest_dir is None:
        dest_dir = Path(__file__).parent / "binaries"
    
    downloaded = []
    failed = []
    
    for platform_key in WITNESS_PLATFORMS.keys():
        print(f"\n{'='*60}")
        print(f"Downloading for platform: {platform_key}")
        print('='*60)
        
        try:
            result = download_witness_binary(platform_key, dest_dir)
            if result:
                downloaded.append((platform_key, result))
            else:
                failed.append(platform_key)
        except Exception as e:
            print(f"Error downloading for {platform_key}: {e}")
            failed.append(platform_key)
    
    print(f"\n{'='*60}")
    print("Download Summary")
    print('='*60)
    
    if downloaded:
        print("\nSuccessfully downloaded:")
        for platform_key, path in downloaded:
            print(f"  {platform_key}: {path.name}")
    
    if failed:
        print("\nFailed downloads:")
        for platform_key in failed:
            print(f"  {platform_key}")
    
    return downloaded, failed


def main():
    """Main entry point for the download script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download witness binaries for bundling with conda"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download binaries for all supported platforms"
    )
    parser.add_argument(
        "--platform",
        choices=["linux_x86_64", "linux_aarch64", "darwin_x86_64", "darwin_arm64", "windows_x86_64"],
        help="Download for specific platform"
    )
    parser.add_argument(
        "--dest",
        type=str,
        help="Destination directory for binaries"
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Witness version to download (e.g., v0.7.0)"
    )
    
    args = parser.parse_args()
    
    if args.version:
        global WITNESS_VERSION
        WITNESS_VERSION = args.version
    
    if args.all:
        download_all_platforms(args.dest)
    elif args.platform:
        # Parse platform string
        parts = args.platform.split("_")
        system = parts[0].capitalize()
        if system == "Darwin":
            system = "Darwin"  # macOS
        elif system == "Windows":
            system = "Windows"
        else:
            system = "Linux"
        
        machine = "_".join(parts[1:])
        download_witness_binary((system, machine), args.dest)
    else:
        # Download for current platform
        result = download_witness_binary(None, args.dest)
        if result:
            print(f"\nWitness binary available at: {result}")
            
            # Test the binary
            print("\nTesting witness binary:")
            os.system(f"{result} version")


if __name__ == "__main__":
    main()