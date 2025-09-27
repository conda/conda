# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda verify`.

Verify packages and environments using in-toto/witness attestations.
"""

from __future__ import annotations

import os
import sys
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction

log = getLogger(__name__)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from .helpers import add_parser_json
    
    summary = "Verify packages and environments using in-toto/witness attestations."
    description = (
        "Verify conda packages and environments against in-toto attestations and policies "
        "using the witness verification tool. This ensures the integrity and provenance "
        "of your conda packages."
    )
    epilog = (
        "Examples:\n"
        "  conda verify --package numpy --policy policy.yaml\n"
        "  conda verify --env --policy policy.yaml --attestations attest.json\n"
        "  conda verify --package pandas --policy policy.yaml --publickey key.pub"
    )

    p = sub_parsers.add_parser(
        "verify",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    
    add_parser_json(p)
    
    # Target selection
    target_group = p.add_mutually_exclusive_group()
    target_group.add_argument(
        "--package",
        metavar="PACKAGE",
        help="Name of the package to verify",
    )
    target_group.add_argument(
        "--env",
        action="store_true",
        help="Verify the current conda environment",
    )
    target_group.add_argument(
        "--prefix",
        metavar="PATH",
        help="Path to conda environment to verify",
    )
    target_group.add_argument(
        "-f", "--artifactfile",
        metavar="PATH",
        help="Path to a specific artifact file to verify",
    )
    target_group.add_argument(
        "--directory-path",
        metavar="PATH",
        help="Path to a directory to verify",
    )
    
    # Policy and key options
    p.add_argument(
        "-p", "--policy",
        required=True,
        metavar="PATH",
        help="Path to the in-toto policy to verify against",
    )
    p.add_argument(
        "-k", "--publickey",
        metavar="PATH",
        help="Path to the policy signer's public key",
    )
    
    # Attestation options
    p.add_argument(
        "-a", "--attestations",
        action="append",
        metavar="PATH",
        help="Attestation files to test against the policy (can be specified multiple times)",
    )
    p.add_argument(
        "-s", "--subjects",
        action="append",
        metavar="SUBJECT",
        help="Additional subjects to lookup attestations (can be specified multiple times)",
    )
    
    # Archivista options
    p.add_argument(
        "--enable-archivista",
        action="store_true",
        help="Use Archivista to store or retrieve attestations",
    )
    p.add_argument(
        "--archivista-server",
        metavar="URL",
        default="https://archivista.testifysec.io",
        help="URL of the Archivista server (default: https://archivista.testifysec.io)",
    )
    p.add_argument(
        "--archivista-token",
        metavar="TOKEN",
        help="Token to use for authentication to Archivista",
    )
    
    # Policy verification options
    p.add_argument(
        "--policy-ca-roots",
        action="append",
        metavar="PATH",
        help="Paths to CA root certificates for verifying x.509 signed policies",
    )
    p.add_argument(
        "--policy-ca-intermediates",
        action="append",
        metavar="PATH",
        help="Paths to CA intermediate certificates for verifying x.509 signed policies",
    )
    
    # Pass-through options for witness
    p.add_argument(
        "--witness-options",
        metavar="OPTIONS",
        help="Additional options to pass directly to witness verify command",
    )
    
    p.set_defaults(func="conda.cli.main_verify.execute")
    
    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """
    Execute the conda verify command.
    
    This command wraps the witness verify CLI tool to provide
    attestation verification for conda packages and environments.
    """
    from ..base.context import context
    from ..witness import (
        check_witness_installed,
        find_package_artifact,
        run_witness_verify,
        resolve_environment_path,
    )
    
    # Check if witness is installed
    if not check_witness_installed():
        from ..exceptions import CondaError
        raise CondaError(
            "The 'witness' CLI tool is not installed or not in PATH.\n"
            "Please install witness from https://github.com/in-toto/witness\n"
            "or ensure it is available in your system PATH."
        )
    
    # Determine what to verify
    artifact_path = None
    subjects = args.subjects or []
    
    if args.package:
        # Find the package artifact in the conda cache
        artifact_path = find_package_artifact(args.package, context)
        if not artifact_path:
            from ..exceptions import PackageNotFoundError
            raise PackageNotFoundError(args.package)
        log.info(f"Verifying package: {args.package} at {artifact_path}")
        
    elif args.env:
        # Verify current environment
        artifact_path = resolve_environment_path(context.active_prefix)
        log.info(f"Verifying current environment at: {artifact_path}")
        
    elif args.prefix:
        # Verify specified environment
        artifact_path = resolve_environment_path(args.prefix)
        log.info(f"Verifying environment at: {artifact_path}")
        
    elif args.artifactfile:
        # Use provided artifact file directly
        artifact_path = Path(args.artifactfile).resolve()
        if not artifact_path.exists():
            from ..exceptions import CondaError
            raise CondaError(f"Artifact file not found: {args.artifactfile}")
            
    elif args.directory_path:
        # Use provided directory directly
        artifact_path = Path(args.directory_path).resolve()
        if not artifact_path.exists():
            from ..exceptions import CondaError
            raise CondaError(f"Directory not found: {args.directory_path}")
    else:
        from ..exceptions import CondaError
        raise CondaError(
            "Please specify what to verify: --package, --env, --prefix, "
            "--artifactfile, or --directory-path"
        )
    
    # Build witness verify command arguments
    witness_args = {
        "policy": args.policy,
        "publickey": args.publickey,
        "attestations": args.attestations,
        "subjects": subjects,
        "artifact_path": str(artifact_path),
        "is_directory": artifact_path.is_dir() if artifact_path else False,
        "enable_archivista": args.enable_archivista,
        "archivista_server": args.archivista_server,
        "archivista_token": args.archivista_token,
        "policy_ca_roots": args.policy_ca_roots,
        "policy_ca_intermediates": args.policy_ca_intermediates,
        "extra_options": args.witness_options,
    }
    
    # Run witness verify
    try:
        result = run_witness_verify(**witness_args)
        
        if context.json:
            from ..cli.common import print_json_and_exit
            print_json_and_exit({
                "verified": result.returncode == 0,
                "artifact": str(artifact_path),
                "policy": args.policy,
                "message": "Verification successful" if result.returncode == 0 else "Verification failed",
                "witness_output": result.stdout,
            })
        else:
            if result.returncode == 0:
                print("✓ Verification successful")
                if result.stdout:
                    print(result.stdout)
            else:
                print("✗ Verification failed", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                elif result.stdout:
                    print(result.stdout, file=sys.stderr)
                    
        return result.returncode
        
    except Exception as e:
        from ..exceptions import CondaError
        raise CondaError(f"Error during verification: {e}")