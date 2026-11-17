# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import pickle
import random

import pytest

from conda.models.build_string import BuildString, _split


def test_build_string_numeric_ordering():
    """Ensure numeric build tokens are sorted numerically, not lexicographically."""
    b2 = BuildString("py312h1234567_2")
    b10 = BuildString("py312h1234567_10")
    assert b2 < b10
    assert b10 > b2
    assert b2 <= b10
    assert b10 >= b2
    assert b2 != b10

    # Test plain numbers
    assert BuildString("2") < BuildString("10")
    assert BuildString("_2") < BuildString("_10")
    assert BuildString("9") < BuildString("11")


def test_build_string_suffix_ordering():
    """Ensure variant suffixes after the build number are compared correctly."""
    b_plain = BuildString("py312h1234_0")
    b_cpu = BuildString("py312h1234_0_cpu")
    b_cuda = BuildString("py312h1234_0_cuda")
    b_openblas = BuildString("py312h1234_0_openblas")

    # Empty tail sorts before non-empty tail
    assert b_plain < b_cpu
    assert b_cpu < b_cuda
    assert b_cuda < b_openblas

    assert b_cuda.suffix == "cuda"
    assert b_cpu.suffix == "cpu"
    assert b_plain.suffix == ""


def test_build_string_no_numeric_token():
    """Ensure build strings without purely numeric tokens sort before numbered builds."""
    b_no_num = BuildString("nompi_h04dc544")
    b_cpu = BuildString("cpu")
    b_mkl = BuildString("mkl")
    b_num = BuildString("h1234567_0")

    assert b_no_num.build_number is None
    assert b_cpu.build_number is None
    assert b_mkl.build_number is None

    assert b_no_num < b_num
    assert b_cpu < b_num
    assert b_mkl < b_num

    # Deterministic alphabetical ordering between non-numbered builds
    assert b_cpu < b_mkl


def test_build_string_pypy_special_case():
    """Ensure python/cross-python PyPy ABI pattern correctly extracts build number."""
    bs = BuildString("14_73_pypy")
    assert bs.build_number == 14
    assert bs.suffix == "73_pypy"

    bs_older = BuildString("2_73_pypy")
    assert bs_older < bs
    assert bs_older.build_number == 2


def test_build_string_mixed_comparisons():
    """Ensure BuildString compares consistently against plain str instances."""
    bs2 = BuildString("py312_2")
    str10 = "py312_10"

    assert bs2 < str10
    assert not (bs2 > str10)
    assert bs2 <= str10
    assert not (bs2 >= str10)

    # Inverted operand order (str compared to BuildString)
    assert str10 > bs2
    assert not (str10 < bs2)
    assert str10 >= bs2
    assert not (str10 <= bs2)

    # Equality against plain str
    assert bs2 == "py312_2"
    assert "py312_2" == bs2
    assert bs2 != "py312_10"
    assert "py312_10" != bs2


def test_build_string_unsupported_operands():
    """Ensure unsupported operand types raise TypeError on comparison."""
    bs = BuildString("py312_2")
    for bad in (None, 2, [2], {"build": "2"}):
        with pytest.raises(TypeError):
            _ = bs < bad
        with pytest.raises(TypeError):
            _ = bs <= bad
        with pytest.raises(TypeError):
            _ = bs > bad
        with pytest.raises(TypeError):
            _ = bs >= bad


def test_build_string_equality_and_hash():
    """Ensure BuildString preserves str equality and hash semantics."""
    s = "py312h1234_3_cuda"
    bs = BuildString(s)
    assert bs == s
    assert hash(bs) == hash(s)

    mapping = {bs: "value"}
    assert mapping[s] == "value"
    assert s in mapping
    assert bs in mapping


def test_build_string_transitivity():
    """Ensure transitivity holds: a < b and b < c implies a < c."""
    items = [
        BuildString("cpu"),
        BuildString("mkl"),
        BuildString("h1234_0"),
        BuildString("h1234_0_cpu"),
        BuildString("h1234_0_cuda"),
        BuildString("h1234_1"),
        BuildString("h1234_10"),
        BuildString("h1234_11"),
    ]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            assert items[i] < items[j]
            assert not (items[j] < items[i])
            for k in range(j + 1, len(items)):
                assert items[i] < items[k]


def test_build_string_shuffled_sorting():
    """Ensure sorting shuffled inputs is deterministic and matches expected order."""
    expected = [
        "cpu",
        "mkl",
        "h1234_0",
        "h1234_1_cpu",
        "h1234_1_cuda",
        "h1234_2",
        "h1234_10",
        "14_73_pypy",
        "h1234_100",
    ]
    shuffled = [BuildString(s) for s in expected]
    rng = random.Random(42)
    for _ in range(10):
        rng.shuffle(shuffled)
        assert sorted(shuffled) == [BuildString(s) for s in expected]
        # Also test key=BuildString.key on plain strings
        str_shuffled = [str(x) for x in shuffled]
        assert sorted(str_shuffled, key=BuildString.key) == expected


def test_build_string_serialization():
    """Ensure BuildString serializes to JSON and pickle identically to str."""
    bs = BuildString("py312h1234_10")
    json_str = json.dumps({"build": bs})
    assert json_str == '{"build": "py312h1234_10"}'
    loaded = json.loads(json_str)
    assert loaded["build"] == "py312h1234_10"

    pickled = pickle.dumps(bs)
    unpickled = pickle.loads(pickled)
    assert unpickled == bs
    assert isinstance(unpickled, BuildString)


def test_build_string_cep26_validation():
    """Ensure CEP 26 validation correctly identifies conforming strings."""
    assert BuildString("py312h1234_0").is_cep26_valid
    assert BuildString("14_73_pypy").is_cep26_valid
    assert BuildString("a.b+c_1").is_cep26_valid

    # Disallowed characters
    assert not BuildString("py 312_0").is_cep26_valid
    assert not BuildString("py@312").is_cep26_valid
    # Exceeding 64 characters
    assert not BuildString("a" * 65).is_cep26_valid


def test_build_string_bounded_cache():
    """Ensure _split cache is bounded to 4096 entries to prevent unbounded memory growth."""
    info = _split.cache_info()
    assert info.maxsize == 4096
