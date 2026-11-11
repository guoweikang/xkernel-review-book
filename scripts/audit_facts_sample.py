"""Audit one archived facts sample against its manifest and fixed Git source."""

import argparse
from collections import Counter
import ctypes
import ctypes.util
import hashlib
import json
from pathlib import Path
import subprocess


def decompress(raw):
    library = ctypes.util.find_library("zstd")
    if not library:
        raise ValueError("System libzstd is required")
    decoder = ctypes.CDLL(library)
    decoder.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    decoder.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
    decoder.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.c_void_p, ctypes.c_size_t]
    decoder.ZSTD_decompress.restype = ctypes.c_size_t
    decoder.ZSTD_isError.argtypes = [ctypes.c_size_t]
    decoder.ZSTD_isError.restype = ctypes.c_uint
    size = decoder.ZSTD_getFrameContentSize(raw, len(raw))
    if not 0 < size <= 64 * 1024 * 1024:
        raise ValueError("Unknown, invalid or oversized frame (limit: 64 MiB)")
    output = ctypes.create_string_buffer(size)
    actual = decoder.ZSTD_decompress(output, size, raw, len(raw))
    if decoder.ZSTD_isError(actual) or actual != size:
        raise ValueError("Decompression failed or size mismatch")
    return output.raw


def audit(repo, manifest_path, sample_path):
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    raw = sample_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    matches = [entry for entry in manifest["crates"] if entry["sha256"] == digest]
    if len(matches) != 1:
        raise ValueError("Sample must match exactly one manifest entry")
    decoded = decompress(raw)
    records = [json.loads(line) for line in decoded.splitlines()]
    entry = matches[0]
    if (entry["bytes"] != len(decoded) or entry["compressed_bytes"] != len(raw)
            or entry["records"] != len(records)):
        raise ValueError("Manifest byte or record count mismatch")
    if records[0]["t"] != "crate" or records[-1]["t"] != "counts":
        raise ValueError("Missing crate header or counts footer")
    header = records[0]
    for field in ("crate_id", "stem", "package", "version", "kind"):
        if header[field] != entry[field]:
            raise ValueError(f"Header does not match manifest entry: {field}")
    if header["schema"] != manifest["schema"] or header["target"] != manifest["target"]:
        raise ValueError("Header does not match manifest schema/target")
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", manifest["commit"] + "^{commit}"],
        text=True).strip()
    items = [record for record in records if record["t"] == "item"]
    paths = sorted({item["file"] for item in items})
    source = {}
    for path in paths:
        result = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                                capture_output=True)
        source[path] = ({"sha256": hashlib.sha256(result.stdout).hexdigest(),
                         "lines": len(result.stdout.splitlines())}
                        if result.returncode == 0 else None)
    invalid_ranges = [item["key"] for item in items if source[item["file"]] is None
                      or not 1 <= item["line"] <= item["end_line"]
                      <= source[item["file"]]["lines"]]
    keys = Counter(item["key"] for item in items)
    return {
        "schema": "facts-sample-audit/1", "commit": commit,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "sample_sha256": digest, "compressed_bytes": len(raw),
        "manifest_entry": matches[0], "header": header,
        "records": len(records),
        "record_types": dict(sorted(Counter(row["t"] for row in records).items())),
        "item_kinds": dict(sorted(Counter(row["kind"] for row in items).items())),
        "fields_by_record_type": {
            kind: sorted({field for row in records if row["t"] == kind for field in row})
            for kind in sorted({row["t"] for row in records})},
        "generated_items": sum(bool(item.get("gen")) for item in items),
        "duplicate_item_keys": sorted(key for key, count in keys.items() if count > 1),
        "invalid_item_line_ranges": invalid_ranges,
        "source_files": source, "exporter_counts": records[-1]["counts"],
        "limitations": [
            "One crate and one configuration; not a corpus coverage estimate.",
            "In-bounds lines do not prove correct identity, exact spans or complete bodies.",
            "Macro callsites and out-of-line modules require separate source resolution.",
            "Source hashes identify local Git bytes, not the original CI working tree bytes.",
            "No semantic correctness, runtime reachability or duplication judgment tested.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = audit(arguments.repo, arguments.manifest, arguments.sample)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in
                     ("commit", "records", "record_types", "generated_items",
                      "duplicate_item_keys", "invalid_item_line_ranges")}, indent=2))


if __name__ == "__main__":
    main()
