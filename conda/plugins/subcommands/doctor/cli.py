# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import argparse
from . import health_checks

parser = argparse.ArgumentParser("conda doctor")


def display_health_check(health_check: health_checks.HealthCheck) -> None:
    print(health_check.title)
    print(health_check.description)
