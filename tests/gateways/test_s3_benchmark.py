# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
S3 download benchmark test.

This test measures real-world S3 download performance by timing conda install
of a large package from S3. It is skipped by default and only runs when
explicitly opted in.

Usage:
    pytest tests/gateways/test_s3_benchmark.py -v --run-s3-benchmark

    # Or with a specific bucket:
    pytest tests/gateways/test_s3_benchmark.py -v --run-s3-benchmark --s3-benchmark-bucket-name=my-bucket
"""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import time
import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

PACKAGE_NAME = "s3-benchmark-test"
PACKAGE_VERSION = "1.0.0"
PACKAGE_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 1GB


def get_bucket_region(bucket_name: str) -> str:
    """Get bucket region using HeadBucket."""
    import boto3

    client = boto3.client("s3")
    response = client.head_bucket(Bucket=bucket_name)
    region = response["ResponseMetadata"]["HTTPHeaders"].get(
        "x-amz-bucket-region", "us-east-1"
    )
    return region


def create_bucket(bucket_name: str) -> str:
    """Create an S3 bucket and return its region."""
    import boto3

    client = boto3.client("s3")
    # Get default region from session
    session = boto3.session.Session()
    region = session.region_name or "us-east-1"

    if region == "us-east-1":
        client.create_bucket(Bucket=bucket_name)
    else:
        client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    return region


def delete_bucket(bucket_name: str, region: str):
    """Delete an S3 bucket and all its contents."""
    import boto3

    client = boto3.client("s3", region_name=region)

    # Delete all objects first
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get("Contents", []):
            client.delete_object(Bucket=bucket_name, Key=obj["Key"])

    client.delete_bucket(Bucket=bucket_name)


def create_test_package(output_dir: Path, size_bytes: int) -> Path:
    """Create a minimal conda package with a large random file."""
    pkg_dir = output_dir / f"{PACKAGE_NAME}-{PACKAGE_VERSION}-0"
    pkg_dir.mkdir(parents=True)

    info_dir = pkg_dir / "info"
    info_dir.mkdir()

    # index.json - minimal package metadata
    index = {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "build": "0",
        "build_number": 0,
        "depends": [],
        "subdir": "noarch",
    }
    (info_dir / "index.json").write_text(json.dumps(index))

    # paths.json
    paths = {
        "paths": [{"_path": "data/large_file.bin", "path_type": "hardlink"}],
        "paths_version": 1,
    }
    (info_dir / "paths.json").write_text(json.dumps(paths))

    # Create large random file
    data_dir = pkg_dir / "data"
    data_dir.mkdir()
    large_file = data_dir / "large_file.bin"

    chunk_size = 64 * 1024 * 1024  # 64MB chunks
    bytes_written = 0
    with open(large_file, "wb") as f:
        while bytes_written < size_bytes:
            chunk = os.urandom(min(chunk_size, size_bytes - bytes_written))
            f.write(chunk)
            bytes_written += len(chunk)

    # Create tarball
    tarball_path = output_dir / f"{PACKAGE_NAME}-{PACKAGE_VERSION}-0.tar.bz2"
    with tarfile.open(tarball_path, "w:bz2") as tar:
        for file_path in pkg_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(pkg_dir)
                tar.add(file_path, arcname=arcname)

    shutil.rmtree(pkg_dir)
    return tarball_path


def create_repodata(output_dir: Path, tarball_path: Path) -> Path:
    """Create minimal repodata.json for the package."""
    import hashlib

    stat = tarball_path.stat()
    with open(tarball_path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()

    repodata = {
        "info": {"subdir": "noarch"},
        "packages": {
            tarball_path.name: {
                "name": PACKAGE_NAME,
                "version": PACKAGE_VERSION,
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": md5,
                "size": stat.st_size,
                "subdir": "noarch",
            }
        },
        "packages.conda": {},
        "repodata_version": 1,
    }

    repodata_path = output_dir / "repodata.json"
    repodata_path.write_text(json.dumps(repodata))
    return repodata_path


def upload_to_s3(bucket: str, region: str, local_path: Path, s3_key: str):
    """Upload a file to S3."""
    import boto3

    client = boto3.client("s3", region_name=region)
    client.upload_file(str(local_path), bucket, s3_key)


@pytest.mark.s3_benchmark
def test_s3_download_benchmark(tmp_path: Path, request):
    """
    Benchmark S3 download performance by installing a large package.

    This test:
    1. Creates a random S3 bucket (or uses provided bucket name)
    2. Creates a 1GB conda package with random data
    3. Uploads it to S3
    4. Times conda install from S3
    5. Cleans up the bucket and test environment
    """
    bucket = request.config.getoption("--s3-benchmark-bucket-name")
    created_bucket = False

    if not bucket:
        bucket = f"conda-s3-benchmark-{uuid.uuid4().hex[:12]}"
        print(f"\nCreating bucket: {bucket}")
        region = create_bucket(bucket)
        created_bucket = True
    else:
        region = get_bucket_region(bucket)

    print(f"Using bucket: {bucket} in region: {region}")

    try:
        # Create test package
        print(
            f"Creating {PACKAGE_SIZE_BYTES / 1024 / 1024 / 1024:.1f}GB test package..."
        )
        start = time.time()
        tarball_path = create_test_package(tmp_path, PACKAGE_SIZE_BYTES)
        print(f"Package created in {time.time() - start:.1f}s: {tarball_path}")

        # Create repodata
        repodata_path = create_repodata(tmp_path, tarball_path)

        # Upload to S3
        print("Uploading to S3...")
        start = time.time()

        tarball_key = f"noarch/{tarball_path.name}"
        upload_to_s3(bucket, region, tarball_path, tarball_key)

        repodata_key = "noarch/repodata.json"
        upload_to_s3(bucket, region, repodata_path, repodata_key)

        print(f"Upload completed in {time.time() - start:.1f}s")

        # Run conda install benchmark
        env_path = tmp_path / "test-env"
        channel = f"s3://{bucket}"

        print(f"\nBenchmarking conda install from {channel}...")

        from conda.cli.main import main_subshell

        start = time.time()
        main_subshell(
            "create",
            "--prefix",
            str(env_path),
            "--channel",
            channel,
            "--override-channels",
            PACKAGE_NAME,
            "--yes",
            "--quiet",
        )
        elapsed = time.time() - start

        package_size_mb = PACKAGE_SIZE_BYTES / 1024 / 1024
        speed_mbps = package_size_mb / elapsed

        print(f"\n{'=' * 50}")
        print("BENCHMARK RESULTS")
        print(f"{'=' * 50}")
        print(f"Package size: {package_size_mb:.0f} MB")
        print(f"Download + install time: {elapsed:.2f}s")
        print(f"Effective speed: {speed_mbps:.1f} MB/s")
        print(f"{'=' * 50}\n")

    finally:
        if created_bucket:
            print(f"Deleting bucket: {bucket}")
            try:
                delete_bucket(bucket, region)
                print("Bucket deleted")
            except Exception as e:
                print(f"Failed to delete bucket: {e}")
