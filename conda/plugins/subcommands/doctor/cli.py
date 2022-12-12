# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import argparse
from . import health_checks

parser = argparse.ArgumentParser(
    "conda doctor", description="Display a health report for your environment."
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="generate a detailed environment health report"
)
args = parser.parse_args()

if args.verbose:
    print("A detailed health report is given below:")
    packages = health_checks.find_packages_with_missing_files
    print(health_checks.format_error_message(packages))

def display_health_check(health_check: health_checks.HealthCheck) -> None:
    print(health_check.title)
    print(health_check.description)
