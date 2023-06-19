# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import random
import types
import unittest
from contextlib import contextmanager
from unittest import mock

from conda.exceptions import SpecNotFound
from conda_env import specs

true_func = mock.Mock(return_value=True)
false_func = mock.Mock(return_value=False)


@contextmanager
def patched_specs(*new_specs):
    with mock.patch.object(specs, "all_specs") as all_specs:
        all_specs.__iter__.return_value = new_specs
        yield all_specs


def generate_two_specs():
    spec1 = mock.Mock(can_handle=false_func)
    spec1.return_value = spec1
    spec2 = mock.Mock(can_handle=true_func)
    spec2.return_value = spec2
    return spec1, spec2


class DetectTestCase(unittest.TestCase):
    def test_has_detect_function(self):
        self.assertTrue(hasattr(specs, "detect"))
        self.assertIsInstance(specs.detect, types.FunctionType)

    def test_dispatches_to_registered_specs(self):
        spec1, spec2 = generate_two_specs()
        with patched_specs(spec1, spec2):
            actual = specs.detect(name="foo")
            self.assertEqual(actual, spec2)

    def test_passes_kwargs_to_all_specs(self):
        random_kwargs = {
            "foo": random.randint(100, 200),
            "bar%d" % random.randint(100, 200): True,
        }

        spec1, spec2 = generate_two_specs()
        with patched_specs(spec1, spec2):
            specs.detect(**random_kwargs)
        spec1.assert_called_with(**random_kwargs)
        spec2.assert_called_with(**random_kwargs)

    def test_raises_exception_if_no_detection(self):
        spec1 = generate_two_specs()[0]
        spec1.msg = "msg"
        with patched_specs(spec1):
            with self.assertRaises(SpecNotFound):
                specs.detect(name="foo")

    def test_has_build_msg_function(self):
        self.assertTrue(hasattr(specs, "build_message"))
        self.assertIsInstance(specs.build_message, types.FunctionType)

    def test_build_msg(self):
        spec3 = mock.Mock(msg="error 3")
        spec4 = mock.Mock(msg="error 4")
        spec5 = mock.Mock(msg=None)
        self.assertEqual(specs.build_message([spec3, spec4, spec5]), "error 3\nerror 4")
