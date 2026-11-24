"""Inventory a ReviewBench manifest and golden files without inference or checkout."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(manifest, golden_dir):
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must be a nonempty list")
    errors = []
    keys = set()
    categories = Counter()
    labels = Counter()
    sources = Counter()
    repositories = Counter()
    rows = []
    files = {manifest.name: digest(manifest)}
    for entry in entries:
        for field in ("repo", "nwo", "pr_number", "base", "head", "title", "body"):
            if field not in entry:
                raise ValueError(f"missing manifest field: {field}")
        key = f"{entry['nwo'].replace('/', '_')}_{entry['pr_number']}-{entry['head'][:8]}"
        if key in keys:
            errors.append(f"duplicate task key: {key}")
        keys.add(key)
        repositories[entry["nwo"]] += 1
        for field in ("base", "head"):
            if not re.fullmatch(r"[0-9a-f]{40}", entry[field]):
                errors.append(f"{key}: invalid {field}")
        path = golden_dir / f"{key}.json"
        if not path.is_file():
            errors.append(f"missing golden: {key}")
            continue
        files[f"{golden_dir.name}/{path.name}"] = digest(path)
        golden = json.loads(path.read_text())
        if golden.get("pr_key") != key:
            errors.append(f"{key}: pr_key mismatch")
        for field in ("repo", "pr_number", "base", "head"):
            if golden.get("pr", {}).get(field) != entry[field]:
                errors.append(f"{key}: golden {field} mismatch")
        findings = golden.get("findings")
        if not isinstance(findings, list):
            errors.append(f"{key}: missing findings array")
            continue
        for index, finding in enumerate(findings):
            pointer = f"{path.name}#/findings/{index}"
            start, end = finding.get("start_line"), finding.get("end_line")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                errors.append(f"{pointer}: invalid line range")
            if finding.get("tp_fp") not in ("tp", "fp"):
                errors.append(f"{pointer}: invalid label")
            if not finding.get("message") or not finding.get("file"):
                errors.append(f"{pointer}: missing message/file")
            category = finding.get("category", "missing")
            source = finding.get("source", {})
            categories[category] += 1
            labels[finding.get("tp_fp", "missing")] += 1
            sources[source.get("type", "missing")] += 1
            rows.append({
                "pointer": pointer, "task": key, "category": category,
                "tp_fp": finding.get("tp_fp"), "file": finding.get("file"),
                "source_url": source.get("url"),
                "source_commit_matches_head": source.get("original_commit") == entry["head"],
            })
    return {
        "schema": "reviewbench-intake/1", "tasks": len(entries),
        "repositories": dict(sorted(repositories.items())),
        "findings": len(rows), "categories": dict(sorted(categories.items())),
        "labels": dict(sorted(labels.items())), "source_types": dict(sorted(sources.items())),
        "unreferenced_goldens": sorted(path.name for path in golden_dir.glob("*.json") if path.stem not in keys),
        "errors": errors, "files_sha256": files, "finding_index": rows,
        "limits": ["No remote comment, patch, line-content or acceptance verification",
                   "Categories are supplied labels, not independently confirmed design issues",
                   "No model inference, detection score or complete schema validation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.manifest, args.golden)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("tasks", "findings", "categories", "labels", "errors")}, ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
