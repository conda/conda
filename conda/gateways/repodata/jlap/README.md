# Layered on-disk format for JLAP patched repodata

Conda's JLAP feature reduces the network bandwidth needed to update a local
index. In the current implementation, conda maintains the complete
`repodata.json` on disk as a single file such as
`$CONDA_PREFIX/pkgs/cache/497deca9.json` with cache headers in an accompanying
`*.info.json`. When the remote index has changed, conda downloads new patches,
applies them to `repodata.json`, and re-serializes the complete file to disk.
For `conda-forge/linux-64` this can mean about 2 seconds to parse a 200+MB JSON
file, a fraction of a second applying patches, and another 2 seconds
re-serialising JSON to disk. On my machine the "serialize complete patched
repodata" strategy is slower than downloading and decompressing
`repodata.json.zst` when the user's bandwidth exceeds about 110 Mbps; but the
write-patched strategy is still faster than downloading `repodata.json` with
`Content-Encoding: gzip`.

We observe that the overwhelming bulk of `repodata.json` is in one of three
top-level objects `packages`, `packages.conda` or the less common `signatures`
(for `conda-content-trust`); all with a key per package filename and a value
holding metadata. Patches will usually add, and sometimes remove or modify, keys
in these objects.

By employing a simple copy-on-write technique for these objects and the
top-level object, conda can accumulate relevant patches into a single, much
smaller overlay that is trivial to read in the solver.

## Collect patches

Selected [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902) patch operations and JSON Pointer values:

```
add /packages.conda/checkov-3.0.24-py310hff52083_0.conda
add /packages.conda/pyarrow-tests-12.0.1-py38h296dbf9_22_cuda.conda/license_family
add /packages.conda/airflow-with-virtualenv-2.7.3-py310hff52083_0.conda/license_family
```

Instead of applying these patches directly to the complete `repodata.json`, we
can collect them into a separate `overlay` object using a copy-on-write
strategy. The `overlay` object starts out looking like

```json
{
    "packages": {},
    "packages.conda": {},
    "signatures": {}
}
```

When a key is added to a top-level object `add
/packages.conda/checkov-3.0.24-py310hff52083_0.conda`, that patch step can be
applied directly to the `overlay` object. (We could apply this patch even
without parsing `repodata.json`, because the [JSON Patch add
operator](https://datatracker.ietf.org/doc/html/rfc6902#section-4.1) will
add-or-replace object keys.)

When a part of a package is modified, `add
/packages.conda/airflow-with-virtualenv-2.7.3-py310hff52083_0.conda/license_family`,
copy `/packages.conda/airflow-with-virtualenv-2.7.3-py310hff52083_0.conda` into
the overlay object. Then apply the patch.

When a value is removed, `remove
/packages.conda/patchelf-0.18.0-h59595ed_1.conda`, write `null` (`None`) as a
deletion marker.

```json
{
    "packages": {},
    "packages.conda": {"patchelf-0.18.0-h59595ed_1.conda": null},
    "signatures": {}
}
```

We accept that a valid `repodata.json` can never contain literal `null` in these
locations, but preserve literal `null` in any other location. (Even though
literall `null` in repodata is usually or always a mistake, the complete schema
is out of scope for this feature.)

### Top level

We apply the same copy-on-write technique to the top level JSON. When a JSON
Patch modifies a top-level key besides `packages`, `packages.conda`, or
`signatures`, we copy that into the overlay before applying the patch.

```json
{
    "info": {},
    "removed": [],
    "packages": {},
    ...
}
```

### Unsupported patch operators

We are interested in the `add`, `remove`, `replace` JSON Patch operators against
the top level and `packages`, `packages.conda`, or `signatures` which are also
the operators the Python [JSON Patch
implementation](https://pypi.org/project/jsonpatch/) generates. An
implementation may choose to fall back to downloading `repodata.json.zst` if the
patch uses other `move, test, copy` operators; when the overlay file grows
beyond a threshold; if there is another error applying patches to the overlay;
or for any other reason.

## Load repodata

A goal of this strategy is that it should be trivial to read from a non-Python
solver.

The solver only uses package records from `packages` and `packages.conda`; and
possibly the subdir from `info`.

When looking up individual package records by key, look up the key in the
overlay. If it is not found look up the record in the full `repodata.json`. If
it is `null` in the overlay then don't send that record to the solver.

When sending all package records to a solver, take the set of keys from
`repodata.json` and the overlay, removing those with `null` values.

## Python implementation

The JSON Patch library only accesses changed object keys, yielding a simple
Python implementation. We override `__getitem__` to implement copy-on-write for
the objects in question. We remove this behavior once the JSON Patch library is
finished.

```python
def __getitem__(self, key):
    try:
        value = self.data[key]
        if value is None:
            # Deletion marker. No explicit None in this dict.
            raise KeyError(key)
        return value
    except KeyError:
        self.data[key] = self.backing[key]
        return self.data[key]
```

### Python API

The `RepodataFetch` class was added to conda in mid-2023, partly to support
bypassing repodata parsing in Python with `fetch_latest_path`. Add
`fetch_latest_path_and_overlay`; update `fetch_latest_parsed` to return an object that
includes changes from the overlay or applies them on demand.

```python
def fetch_latest_parsed(self) -> tuple[dict, RepodataState]:
def fetch_latest_path(self) -> tuple[Path, RepodataState]:
def fetch_latest_path_and_overlay(self) -> tuple[Path, Path, RepodataState]:
```

### Additional `*.info.json` metadata

When jlap is in use, the cache metadata contains additional fields to track the
end of the remote patchset. It looks like this:

```json
{
  "mod": "Mon, 06 Nov 2023 16:54:13 GMT",
  "etag": "W/\"1b86889638274ce7431338402342ca72\"",
  "cache_control": "public, max-age=1200",
  "blake2_256_nominal": "1321162b34cd85637dcfe7d71c57c9afdffc7df44d5389c5feef0b74b1efea95",
  "blake2_256": "1321162b34cd85637dcfe7d71c57c9afdffc7df44d5389c5feef0b74b1efea95",
  "url": "https://conda.anaconda.org/conda-forge/linux-64",
  "size": 223853476,
  "mtime_ns": 1699289888577232522,
  "refresh_ns": 1699289924631359000,
  "has_jlap": {
    "last_checked": "2023-11-06T16:58:44.124601Z",
    "value": true
  },
  "jlap": {
    "headers": {
      "date": "Mon, 06 Nov 2023 16:58:43 GMT",
      "content-type": "text/plain",
      "cache-control": "public, max-age=1200",
      "etag": "W/\"1b86889638274ce7431338402342ca72\"",
      "last-modified": "Mon, 06 Nov 2023 16:54:13 GMT",
      "content-encoding": "gzip"
    },
    "iv": "5ae8babaf0fd279e1f5fce4ebfd2a801a2af440fe4ba19c6ef266e282a6bd0c6",
    "pos": 9445277,
    "footer": {
      "url": "repodata.json",
      "latest": "1321162b34cd85637dcfe7d71c57c9afdffc7df44d5389c5feef0b74b1efea95"
    }
  }
}
```

When the overlay is in use, we may leave the jlap values alone, especially
`"blake2_256_nominal"` and `"blake2_256"` which reflect the hash of the complete
`repodata.json` but not the overlay, so that older clients see an out-of-date
cache.

New values, perhaps a top-level `"overlay"` object, will track the `nominal`
hash of the full `repodata.json` plus the overlay. The `nominal` hash identifies
the complete upstream `repodata.json` tracked for each line in the JLAP
patchset.

## Preliminary results

On my machine, the `accumulate.py` demonstration script takes `0.12` seconds to
`parse JLAP and apply patches`, from a 9.3M JLAP file and producing a 2MB
overlay. Compared to `2.02` seconds to serialize the complete
`conda-forge/linux-64/repodata.json` to disk. Either strategy takes almost
exactly two seconds to first load the 213MB `conda-forge/linux-64/repodata.json`
from disk. The overlay strategy is beneficial to users with much faster network
speeds compared to the original write-patched strategy.
