# Using MTGJSON-slim

[Back to README](../README.md) · [Downloads](https://dreadpool-87.github.io/MTGJSON-slim/) · [Development guide](DEVELOPMENT.md)

This guide covers **downloading and consuming** a published dataset, then **building and validating** a new dataset from the official MTGJSON source. These are separate workflows: you do **not** need to run Python to use a published database.

## 1. Choose and download

| Dataset | Main use | Source shape |
| --- | --- | --- |
| AllPrintings SQLite | Indexed lookup, collection reconciliation, printing/token identities | Eight retained SQL tables and 20 explicit indexes (profile 2.3) |
| AllPrintings JSON | Set-based printing and token records | `meta` + sets under `data`, with card/token arrays |
| AtomicCards JSON | Card-name/Oracle-based lookup | `meta` + name-keyed arrays under `data` |

Visit the [download site](https://dreadpool-87.github.io/MTGJSON-slim/). Each of these datasets is independently built from the appropriate official MTGJSON source. AtomicCards **does not** substitute for individual printings or standalone token records.

All three families offer raw, XZ, Zstandard and ZIP copies. Each download has its own `.sha256` sidecar. When possible, use the sidecar to verify the **compressed file before extraction**, and always verify the extracted bytes if you compare formats. For example, on Linux:

```bash
sha256sum -c YOUR-DOWNLOADED-FILENAME.sha256
```

Keep the data file and its matching sidecar in the same directory when using this command. On Windows, compare the result of `Get-FileHash -Algorithm SHA256 <filename>` with the sidecar. XZ and Zstd files are compressed **single files**; ZIP is a standard archive containing exactly one database/JSON file. For automatic readers, Zstandard supports streaming decompression. The raw `.sqlite` or `.json` files need no extraction.

**Source limitations matter:** SQLite and AllPrintings JSON deliberately remove some translation/product/narrative data. AtomicCards retains nested foreign-language entries, but does not include a full printing or token database. For full printing-level foreign-name searches or product data, consult the official [MTGJSON](https://mtgjson.com/) source and [SQLite field inventory](PROFILE_2_3_DATA_INVENTORY.md).

## 2. Prerequisites for local builds

Local builders are tested on Linux; native Windows builder support has not been verified. Downloaded SQLite/JSON files can still be used by compatible Windows applications. The SQLite builder imports the Unix-only `resource` module. The workflow runners use Python 3.14; the SQLite converter requires Python 3.11+ and no pip packages. The JSON builders use `ijson`, pinned in `requirements-json.txt`:

```bash
python -m pip install -r requirements-json.txt
```

For packaging Zstandard, Python 3.14 provides `compression.zstd` directly; when running older local Python, install the system `zstd` executable. ZIP uses Deflate. The *full* regression suite also needs Node.js for website behavior tests.

AtomicCards source downloads and the complete regression gate also require the system `curl` executable. Downloads allow HTTPS only, at most five redirects, three retries, a 30-second connection timeout and a 360-second timeout per attempt. The destination filesystem must support hard links. Use a **private, trusted destination directory with trusted parent directories**; untrusted processes must not be able to modify its files or temporary staging area.

Both source files are downloaded into temporary staging and checksum-verified before their final names appear; existing files or symlinks are never overwritten. Catchable transfer or publication failures clean up this invocation's files. Publishing two files is not a single filesystem transaction: an abrupt termination (such as `SIGKILL`) can leave a verified checksum sidecar without its archive and/or a `.atomic-download-*` temporary staging directory. These remnants are not reused as verified downloads, and an orphan sidecar blocks a retry. **Inspect and remove only files or staging directories confirmed to belong to the interrupted attempt**, or retry in a new empty destination directory. Never use wildcard cleanup in a shared directory or delete unrelated files.

Use a clean checkout of the specific tool commit recorded in the output manifest. Ensure enough free space for the compressed source, extracted/temporary files and generated database. Generated files are never silently overwritten.

## 3. Build AllPrintings SQLite (profile 2.3)

```bash
python slim.py download --directory downloads --report evidence/download.json
python slim.py build \
  --archive downloads/AllPrintings.sqlite.xz \
  --sha256 "$(cat downloads/AllPrintings.sqlite.xz.sha256)" \
  --profile profiles/v2_3.json --output-dir output \
  --tool-commit "$(git rev-parse HEAD)" --report evidence/build.json
```

`download` retrieves the **official XZ archive and its matching SHA-256**, checks the archive and does not decompress it. `build` automatically inventories the source, validates retained rows and relationships, stages the output and generates raw SQLite, XZ, both sidecars and `manifest.json`.

To inspect the **raw official source** independently, decompress it first:

```bash
xz -dk downloads/AllPrintings.sqlite.xz
python slim.py inventory --database downloads/AllPrintings.sqlite --report evidence/source.json
```

To validate a completed slim database against the official extracted source, replace the version placeholder with the exact filename from `output/manifest.json`:

```bash
python slim.py validate \
  --database output/AllPrintings-slim-VERSION-profile-2.3.sqlite \
  --source downloads/AllPrintings.sqlite --profile profiles/v2_3.json \
  --report evidence/validation.json
```

Without `--source`, validation checks SQLite integrity, schema, identity keys and relationships; with `--source`, it checks projected row counts and logical digests, including duplicates and NULL values. Build reports must be **outside** the output package and must not overwrite inputs.

For checksum-only upstream change detection, `download --previous-sha256 <prior-official-digest>` can return `UNCHANGED` without re-downloading. Repeating a build with identical input/profile/tool settings rechecks the existing output before returning `UNCHANGED`. Different inputs require a new output directory.

`slim.py build` and `validate` default to profile 2.3; older profile 2.2 can be supplied explicitly to reproduce historical results. For an exact table/field list, see the [profile 2.3 inventory](PROFILE_2_3_DATA_INVENTORY.md).

## 4. Build AllPrintings JSON

JSON is built **directly from official AllPrintings JSON**, never by exporting the SQLite output:

```bash
python slim_json.py download --directory downloads-json
python slim_json.py build \
  --archive downloads-json/AllPrintings.json.xz \
  --checksum-path downloads-json/AllPrintings.json.xz.sha256 \
  --output-dir output-json
```

The source SHA-256 is checked before projection. The streaming builder retains set/card/token records, verifies selected values against the independently sourced data and writes the raw JSON, XZ, SHA-256 sidecars and `json-manifest.json`. It refuses to overwrite an existing artifact.

For an additional independent source-field audit, use the actual versioned raw JSON filename from `output-json/json-manifest.json`:

```bash
python scripts/audit_json_field_selection.py \
  --source downloads-json/AllPrintings.json.xz \
  --slim-json output-json/AllPrintings-slim-VERSION.json \
  --report evidence/json-field-audit.json
```

The ZIP and Zstandard variants are produced **after** base validation:

```bash
python scripts/package_json_formats.py \
  --package output-json --report evidence/json-packaging.json
```

The packager checks raw JSON and XZ against the manifest and verifies Zstd/ZIP decompression to **exactly the same JSON SHA-256**. Full field-selection evidence and historical measurements are in the [AllPrintings JSON audit](JSON_DIRECT_SOURCE_PREVIEW.md).

## 5. Build AtomicCards JSON (profile B1)

AtomicCards is a *name-grouped* dataset. It retains the official card groups and nested source values but removes only `purchaseUrls` and the verified redundant `convertedManaCost` / `faceConvertedManaCost` aliases; consumers should use `manaValue` and `faceManaValue`.

```bash
python atomic_slim.py download --directory downloads-atomic
python atomic_slim.py build \
  --archive downloads-atomic/AtomicCards.json.xz \
  --checksum-path downloads-atomic/AtomicCards.json.xz.sha256 \
  --output-dir output-atomic
```

**A build alone is not a publishable package.** The independent auditor must compare every retained nested value against the official source and mark the manifest as verified:

```bash
python scripts/audit_atomic_source.py \
  --source downloads-atomic/AtomicCards.json.xz \
  --checksum-path downloads-atomic/AtomicCards.json.xz.sha256 \
  --raw output-atomic/AtomicCards-slim-VERSION-atomic-b1.json \
  --package output-atomic \
  --report evidence/atomic-retention.json --mark-verified

python atomic_slim.py verify --package output-atomic
python scripts/package_atomic_formats.py \
  --package output-atomic --report evidence/atomic-packaging.json
```

Replace `VERSION` with the version in `output-atomic/atomic-manifest.json`. Both the builder and auditor reject unexpected or duplicate root properties; the retained nested values, group/record counts and original order must match the source. The packager produces Zstd/ZIP with their own SHA-256 sidecars only after validation.

For the exact retention contract, see [atomic-b1.json](../contracts/atomic-b1.json). AtomicCards complements, not replaces, AllPrintings for printing resolution.

## 6. Tests and query benchmark

The complete required regression gate checks Python, JSON, website behavior and archive integrity. Install the pinned parser and provide Node.js plus Python 3.14 native Zstd or an older-runtime CLI fallback:

```bash
python scripts/run_regression_tests.py
```

It returns failure for any failing, skipped or undiscovered tests. Run format-specific commands only when debugging individual components.

For a sampled SQLite lookup benchmark, use saved query cases so results are comparable:

```bash
python benchmarks/query_audit.py --database path/to/database.sqlite \
  --cases cases.json --create-cases --report benchmark.json --repeats 5
```

This captures queries, execution plans, row counts, digests, warm-cache batches, medians and available per-index `dbstat` footprints. Missing `dbstat` is reported as unavailable rather than zero. **It is a sampled benchmark, not a guarantee of cold-cache performance.**

For publication rules, provenance, schema drift, Release handling and troubleshooting, see [Development & automation](DEVELOPMENT.md).
