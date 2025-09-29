# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Utilities for integrating in-toto/witness with conda."""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subprocess import CompletedProcess
    from ..base.context import Context

from typing import Optional

log = getLogger(__name__)

# Path to bundled witness binaries
WITNESS_BINARIES_DIR = Path(__file__).parent / "binaries"


def get_witness_binary_path() -> Optional[Path]:
    """
    Get the path to the witness binary for the current platform.
    
    First checks for bundled binary, then falls back to system PATH.
    
    Returns:
        Path to witness binary if found, None otherwise
    """
    # Determine platform-specific binary name
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize machine architecture
    if machine in ("amd64", "x86_64"):
        machine = "x86_64"
    elif machine in ("aarch64", "arm64"):
        machine = "aarch64" if system == "linux" else "arm64"
    
    # Construct binary name
    binary_name = f"witness_{system}_{machine}"
    if system == "windows":
        binary_name += ".exe"
    
    # Check for bundled binary
    bundled_path = WITNESS_BINARIES_DIR / binary_name
    if bundled_path.exists():
        # Ensure it's executable on Unix-like systems
        if system != "windows":
            try:
                bundled_path.chmod(bundled_path.stat().st_mode | stat.S_IEXEC)
            except Exception as e:
                log.debug(f"Could not set executable permission: {e}")
        
        log.debug(f"Using bundled witness binary: {bundled_path}")
        return bundled_path
    
    # Fall back to system PATH
    system_witness = shutil.which("witness")
    if system_witness:
        log.debug(f"Using system witness binary: {system_witness}")
        return Path(system_witness)
    
    # Try to download the binary if not found
    try:
        from .download_witness import download_witness_binary
        log.info("Witness binary not found, attempting to download...")
        downloaded_path = download_witness_binary()
        if downloaded_path and downloaded_path.exists():
            log.info(f"Downloaded witness binary: {downloaded_path}")
            return downloaded_path
    except Exception as e:
        log.debug(f"Could not download witness binary: {e}")
    
    return None


def check_witness_installed() -> bool:
    """
    Check if the witness CLI tool is available (bundled or in PATH).
    
    Returns:
        True if witness is available, False otherwise
    """
    return get_witness_binary_path() is not None


def find_package_artifact(package_name: str, context: Context) -> Optional[Path]:
    """
    Find a package artifact in the conda package cache.
    
    Args:
        package_name: Name of the package to find
        context: Conda context object
        
    Returns:
        Path to the package artifact if found, None otherwise
    """
    from ..core.package_cache_data import PackageCacheData
    from ..models.match_spec import MatchSpec
    
    # Parse package specification
    spec = MatchSpec(package_name)
    
    # Search in all package cache directories
    for pkgs_dir in context.pkgs_dirs:
        pcd = PackageCacheData(pkgs_dir)
        pcd.reload()
        
        # Find matching packages
        for package_record in pcd.query(spec):
            # Check for .conda or .tar.bz2 files
            pkg_path = Path(pkgs_dir) / package_record.fn
            if pkg_path.exists():
                log.debug(f"Found package artifact: {pkg_path}")
                return pkg_path
                
            # Also check extracted directory
            extracted_path = Path(pkgs_dir) / package_record.extracted_package_dir
            if extracted_path.exists():
                log.debug(f"Found extracted package: {extracted_path}")
                return extracted_path
    
    # Try to find in current environment's conda-meta
    if context.active_prefix:
        conda_meta = Path(context.active_prefix) / "conda-meta"
        if conda_meta.exists():
            # Look for package metadata files
            for meta_file in conda_meta.glob(f"{spec.name}-*.json"):
                log.debug(f"Found package metadata: {meta_file}")
                # Return the environment directory as the artifact to verify
                return Path(context.active_prefix)
    
    log.warning(f"Package artifact not found for: {package_name}")
    return None


def resolve_environment_path(prefix: str) -> Path:
    """
    Resolve and validate a conda environment path.
    
    Args:
        prefix: Path to the conda environment
        
    Returns:
        Resolved Path object
        
    Raises:
        ValueError: If the environment path is invalid
    """
    env_path = Path(prefix).resolve()
    
    if not env_path.exists():
        raise ValueError(f"Environment path does not exist: {prefix}")
    
    # Check if it's a valid conda environment
    conda_meta = env_path / "conda-meta"
    if not conda_meta.exists():
        raise ValueError(f"Not a valid conda environment (no conda-meta): {prefix}")
    
    return env_path


def run_witness_verify(
    policy: str,
    artifact_path: str,
    is_directory: bool = False,
    publickey: Optional[str] = None,
    attestations: Optional[list[str]] = None,
    subjects: Optional[list[str]] = None,
    enable_archivista: bool = False,
    archivista_server: Optional[str] = None,
    archivista_token: Optional[str] = None,
    policy_ca_roots: Optional[list[str]] = None,
    policy_ca_intermediates: Optional[list[str]] = None,
    extra_options: Optional[str] = None,
) -> CompletedProcess:
    """
    Run the witness verify command with the specified arguments.
    
    Args:
        policy: Path to the policy file
        artifact_path: Path to the artifact to verify
        is_directory: Whether the artifact is a directory
        publickey: Path to public key for policy verification
        attestations: List of attestation file paths
        subjects: List of additional subjects
        enable_archivista: Whether to use Archivista
        archivista_server: Archivista server URL
        archivista_token: Archivista authentication token
        policy_ca_roots: CA root certificate paths for policy verification
        policy_ca_intermediates: CA intermediate certificate paths
        extra_options: Additional options to pass to witness
        
    Returns:
        CompletedProcess object with the result of the witness command
        
    Raises:
        FileNotFoundError: If witness binary is not available
    """
    # Get witness binary path
    witness_path = get_witness_binary_path()
    if not witness_path:
        raise FileNotFoundError(
            "Witness binary not found. Please ensure witness is installed "
            "or run 'python -m conda.witness.download_witness' to download it."
        )
    
    # Build witness command
    cmd = [str(witness_path), "verify"]
    
    # Add required arguments
    cmd.extend(["--policy", policy])
    
    # Add artifact specification
    if is_directory:
        cmd.extend(["--directory-path", artifact_path])
    else:
        cmd.extend(["--artifactfile", artifact_path])
    
    # Add optional arguments
    if publickey:
        cmd.extend(["--publickey", publickey])
    
    if attestations:
        for attestation in attestations:
            cmd.extend(["--attestations", attestation])
    
    if subjects:
        for subject in subjects:
            cmd.extend(["--subjects", subject])
    
    if enable_archivista:
        cmd.append("--enable-archivista")
        if archivista_server:
            cmd.extend(["--archivista-server", archivista_server])
        if archivista_token:
            cmd.extend(["--archivista-token", archivista_token])
    
    if policy_ca_roots:
        for ca_root in policy_ca_roots:
            cmd.extend(["--policy-ca-roots", ca_root])
    
    if policy_ca_intermediates:
        for ca_intermediate in policy_ca_intermediates:
            cmd.extend(["--policy-ca-intermediates", ca_intermediate])
    
    # Add any extra options
    if extra_options:
        import shlex
        cmd.extend(shlex.split(extra_options))
    
    log.info(f"Running witness command: {' '.join(cmd)}")
    
    # Execute witness command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit code
        )
        
        log.debug(f"Witness exit code: {result.returncode}")
        if result.stdout:
            log.debug(f"Witness stdout: {result.stdout}")
        if result.stderr:
            log.debug(f"Witness stderr: {result.stderr}")
            
        return result
        
    except subprocess.SubprocessError as e:
        log.error(f"Failed to execute witness command: {e}")
        raise
    except Exception as e:
        log.error(f"Unexpected error running witness: {e}")
        raise


def get_package_info(package_name: str, context: Context) -> dict:
    """
    Get information about a package for verification purposes.
    
    Args:
        package_name: Name of the package
        context: Conda context object
        
    Returns:
        Dictionary with package information
    """
    from ..core.package_cache_data import PackageCacheData
    from ..models.match_spec import MatchSpec
    
    spec = MatchSpec(package_name)
    info = {
        "name": spec.name,
        "found": False,
        "artifacts": [],
    }
    
    for pkgs_dir in context.pkgs_dirs:
        pcd = PackageCacheData(pkgs_dir)
        pcd.reload()
        
        for package_record in pcd.query(spec):
            artifact_info = {
                "version": package_record.version,
                "build": package_record.build,
                "channel": str(package_record.channel),
                "subdir": package_record.subdir,
                "fn": package_record.fn,
                "path": str(Path(pkgs_dir) / package_record.fn),
            }
            
            # Check if file exists
            if Path(artifact_info["path"]).exists():
                artifact_info["exists"] = True
                info["found"] = True
            else:
                artifact_info["exists"] = False
                
            info["artifacts"].append(artifact_info)
    
    return info