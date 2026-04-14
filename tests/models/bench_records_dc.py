# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""A19 benchmarks: Entity-based vs dataclass-based PackageRecord.

Run with pytest:
    pytest tests/models/bench_records_dc.py -v --tb=short

Run with CodSpeed:
    pytest --codspeed tests/models/bench_records_dc.py

Run standalone for quick numbers:
    python tests/models/bench_records_dc.py
"""

from __future__ import annotations

import json
import sys
import timeit
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.models.records import PackageRecord
from conda.models.records_dc import PackageRecordDC

if TYPE_CHECKING:
    from typing import Any

    from pytest_codspeed.plugin import BenchmarkFixture

SAMPLE_KWARGS: dict[str, Any] = dict(
    name="numpy",
    version="1.21.0",
    build="py39hdbf815f_0",
    build_number=0,
    channel="conda-forge",
    subdir="linux-64",
    fn="numpy-1.21.0-py39hdbf815f_0.conda",
    depends=["python >=3.9,<3.10.0a0", "libopenblas >=0.3.15"],
    constrains=["numpy-base <0a0"],
    md5="d4c8e19a8e9c7f8e1a2b3c4d5e6f7a8b",
    sha256="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    timestamp=1625000000000,
    size=7654321,
)

SAMPLE_JSON = json.dumps(SAMPLE_KWARGS)

SCALE = 10_000


@pytest.fixture()
def entity_record() -> PackageRecord:
    return PackageRecord(**SAMPLE_KWARGS)


@pytest.fixture()
def dc_record() -> PackageRecordDC:
    return PackageRecordDC(**SAMPLE_KWARGS)


@pytest.mark.benchmark
def test_instantiate_entity(benchmark: BenchmarkFixture) -> None:
    def target() -> PackageRecord:
        return PackageRecord(**SAMPLE_KWARGS)

    benchmark(target)


@pytest.mark.benchmark
def test_instantiate_dc(benchmark: BenchmarkFixture) -> None:
    def target() -> PackageRecordDC:
        return PackageRecordDC(**SAMPLE_KWARGS)

    benchmark(target)


@pytest.mark.benchmark
def test_dump_entity(benchmark: BenchmarkFixture, entity_record: PackageRecord) -> None:
    benchmark(entity_record.dump)


@pytest.mark.benchmark
def test_dump_dc(benchmark: BenchmarkFixture, dc_record: PackageRecordDC) -> None:
    benchmark(dc_record.dump)


@pytest.mark.benchmark
def test_from_objects_entity(benchmark: BenchmarkFixture) -> None:
    src: dict[str, Any] = SAMPLE_KWARGS.copy()
    benchmark(PackageRecord.from_objects, src)


@pytest.mark.benchmark
def test_from_objects_dc(benchmark: BenchmarkFixture) -> None:
    src: dict[str, Any] = SAMPLE_KWARGS.copy()
    benchmark(PackageRecordDC.from_objects, src)


@pytest.mark.benchmark
def test_hash_entity(benchmark: BenchmarkFixture) -> None:
    records = [
        PackageRecord(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(1000)
    ]

    def target() -> set[PackageRecord]:
        return set(records)

    benchmark(target)


@pytest.mark.benchmark
def test_hash_dc(benchmark: BenchmarkFixture) -> None:
    records = [
        PackageRecordDC(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(1000)
    ]

    def target() -> set[PackageRecordDC]:
        return set(records)

    benchmark(target)


@pytest.mark.benchmark
def test_round_trip_entity(benchmark: BenchmarkFixture) -> None:
    raw = json.loads(SAMPLE_JSON)

    def target() -> str:
        rec = PackageRecord(**raw)
        return json.dumps(rec.dump())

    benchmark(target)


@pytest.mark.benchmark
def test_round_trip_dc(benchmark: BenchmarkFixture) -> None:
    raw = json.loads(SAMPLE_JSON)

    def target() -> str:
        rec = PackageRecordDC(**raw)
        return json.dumps(rec.dump())

    benchmark(target)


@pytest.mark.limit_memory("40 MB")
def test_memory_entity_50k() -> None:
    records = [
        PackageRecord(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(50_000)
    ]
    assert len(records) == 50_000


@pytest.mark.limit_memory("40 MB")
def test_memory_dc_50k() -> None:
    records = [
        PackageRecordDC(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(50_000)
    ]
    assert len(records) == 50_000


def run_standalone() -> None:
    """Quick standalone benchmark printing timings and speedup ratios."""
    number = SCALE

    def time_it(label: str, stmt: str, setup: str = "") -> float:
        full_setup = (
            "from conda.models.records import PackageRecord\n"
            "from conda.models.records_dc import PackageRecordDC\n"
            f"import json\n"
            f"KWARGS = {SAMPLE_KWARGS!r}\n"
            f"JSON_STR = {SAMPLE_JSON!r}\n"
            f"{setup}\n"
        )
        t = timeit.timeit(stmt, setup=full_setup, number=number)
        ms = t * 1000
        per_op = ms / number * 1000
        print(f"  {label:30s}  {ms:8.1f} ms  ({per_op:.2f} µs/op)")
        return t

    print(f"\n{'=' * 60}")
    print(f"A19 Benchmark: Entity vs Dataclass ({number:,} iterations)")
    print(f"{'=' * 60}\n")

    print("Instantiation:")
    t_entity = time_it("Entity", "PackageRecord(**KWARGS)")
    t_dc = time_it("Dataclass", "PackageRecordDC(**KWARGS)")
    print(f"  {'Speedup':30s}  {t_entity / t_dc:.1f}x\n")

    print("dump():")
    t_entity = time_it(
        "Entity",
        "rec.dump()",
        "rec = PackageRecord(**KWARGS)",
    )
    t_dc = time_it(
        "Dataclass",
        "rec.dump()",
        "rec = PackageRecordDC(**KWARGS)",
    )
    print(f"  {'Speedup':30s}  {t_entity / t_dc:.1f}x\n")

    print("from_objects(dict):")
    t_entity = time_it("Entity", "PackageRecord.from_objects(KWARGS)")
    t_dc = time_it("Dataclass", "PackageRecordDC.from_objects(KWARGS)")
    print(f"  {'Speedup':30s}  {t_entity / t_dc:.1f}x\n")

    hash_size = 500
    print(f"hash + set insertion ({hash_size} records):")
    setup_hash = (
        f"records_e = [PackageRecord(**{{**KWARGS, 'name': f'pkg-{{i}}'}}) for i in range({hash_size})]\n"
        f"records_d = [PackageRecordDC(**{{**KWARGS, 'name': f'pkg-{{i}}'}}) for i in range({hash_size})]"
    )
    t_entity = time_it("Entity", "set(records_e)", setup_hash)
    t_dc = time_it("Dataclass", "set(records_d)", setup_hash)
    print(f"  {'Speedup':30s}  {t_entity / t_dc:.1f}x\n")

    print("Round-trip json->construct->dump->json:")
    setup_rt = "raw = json.loads(JSON_STR)"
    t_entity = time_it(
        "Entity",
        "json.dumps(PackageRecord(**raw).dump())",
        setup_rt,
    )
    t_dc = time_it(
        "Dataclass",
        "json.dumps(PackageRecordDC(**raw).dump())",
        setup_rt,
    )
    print(f"  {'Speedup':30s}  {t_entity / t_dc:.1f}x\n")

    run_memory_benchmark()


def run_memory_benchmark() -> None:
    """Measure per-record memory footprint using tracemalloc and sys.getsizeof."""
    from conda.models.records import PackageRecord
    from conda.models.records_dc import PackageRecordDC

    counts = [1, 1_000, 10_000, 50_000]

    print(f"{'=' * 60}")
    print("Memory benchmark")
    print(f"{'=' * 60}\n")

    entity_single = PackageRecord(**SAMPLE_KWARGS)
    dc_single = PackageRecordDC(**SAMPLE_KWARGS)
    entity_shallow = sys.getsizeof(entity_single)
    dc_shallow = sys.getsizeof(dc_single)
    entity_dict_size = (
        sys.getsizeof(entity_single.__dict__)
        if hasattr(entity_single, "__dict__")
        else 0
    )
    print("sys.getsizeof (shallow, single instance):")
    print(
        f"  {'Entity':30s}  {entity_shallow:,} bytes (+ __dict__ {entity_dict_size:,} bytes = {entity_shallow + entity_dict_size:,} total)"
    )
    print(f"  {'Dataclass (slots)':30s}  {dc_shallow:,} bytes (no __dict__)")
    print(
        f"  {'Saving per record':30s}  {entity_shallow + entity_dict_size - dc_shallow:,} bytes ({(entity_shallow + entity_dict_size) / dc_shallow:.1f}x)\n"
    )

    for count in counts:
        tracemalloc.start()
        entity_records = [
            PackageRecord(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(count)
        ]
        entity_current, entity_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        tracemalloc.start()
        dc_records = [
            PackageRecordDC(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"})
            for i in range(count)
        ]
        dc_current, dc_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        entity_per = entity_current / count
        dc_per = dc_current / count

        print(f"{count:,} records (tracemalloc current / peak):")
        print(
            f"  {'Entity':30s}  {entity_current / 1024:,.0f} KiB / {entity_peak / 1024:,.0f} KiB  ({entity_per:.0f} bytes/rec)"
        )
        print(
            f"  {'Dataclass':30s}  {dc_current / 1024:,.0f} KiB / {dc_peak / 1024:,.0f} KiB  ({dc_per:.0f} bytes/rec)"
        )
        print(
            f"  {'Saving':30s}  {(entity_current - dc_current) / 1024:,.0f} KiB  ({entity_per / dc_per:.1f}x per record)\n"
        )

        del entity_records, dc_records


def run_memray_profile() -> None:
    """Generate memray .bin files for flamegraph analysis.

    After running, generate flamegraphs with:
        memray flamegraph memray_entity_50k.bin -o entity_50k.html
        memray flamegraph memray_dc_50k.bin -o dc_50k.html
    """
    try:
        import memray
    except ImportError:
        print("memray not installed, skipping memray profiling")
        return

    from conda.models.records import PackageRecord
    from conda.models.records_dc import PackageRecordDC

    count = 50_000
    output_dir = Path(".")

    print(f"\n{'=' * 60}")
    print(f"Memray profiling ({count:,} records)")
    print(f"{'=' * 60}\n")

    entity_bin = output_dir / "memray_entity_50k.bin"
    dc_bin = output_dir / "memray_dc_50k.bin"

    entity_bin.unlink(missing_ok=True)
    dc_bin.unlink(missing_ok=True)

    print(f"Profiling Entity -> {entity_bin}")
    with memray.Tracker(str(entity_bin)):
        entity_records = [
            PackageRecord(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"}) for i in range(count)
        ]
    del entity_records

    print(f"Profiling Dataclass -> {dc_bin}")
    with memray.Tracker(str(dc_bin)):
        dc_records = [
            PackageRecordDC(**{**SAMPLE_KWARGS, "name": f"pkg-{i}"})
            for i in range(count)
        ]
    del dc_records

    print("\nGenerate flamegraphs with:")
    print(f"  memray flamegraph {entity_bin} -o entity_50k.html")
    print(f"  memray flamegraph {dc_bin} -o dc_50k.html")
    print(f"  memray stats {entity_bin}")
    print(f"  memray stats {dc_bin}")


if __name__ == "__main__":
    run_standalone()
    run_memray_profile()
