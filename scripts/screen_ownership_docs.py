#!/usr/bin/env python3
"""Bounded lexical admission screen on the previously parsed standard library."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in (".", ".."):
        parser.error("run must be a single directory name")
    protocol_path = ROOT / "research/protocols/ownership-family-admission-v1.json"
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / "research/evidence/runs" / protocol["source_run"]
    parent_report = json.loads((parent / "report.json").read_text())
    for name in ("units.json", "files.json"):
        assert sha(parent / name) == parent_report["artifacts_sha256"][name]
    run = ROOT / "research/evidence/runs" / args.run
    run.mkdir(exist_ok=False)
    shutil.copyfile(protocol_path, run / "protocol.json")
    shutil.copyfile(Path(__file__), run / "runner.py")
    files = {row["path"]: row for row in json.loads((parent / "files.json").read_text())}
    units = json.loads((parent / "units.json").read_text())
    parsed, matches = {}, []
    for unit in sorted(units, key=lambda row: row["id"]):
        file = files[unit["path"]]
        if unit["path"] not in parsed:
            path = parent / file["parsed"]
            assert sha(path) == parent_report["artifacts_sha256"][file["parsed"]]
            parsed[unit["path"]] = json.loads(path.read_text())
        attributes = parsed[unit["path"]]["units"][unit["syntax_index"]]["attributes"]
        text = "\n".join(attr["doc_text"] for attr in attributes if attr["path"] == "doc" and isinstance(attr.get("doc_text"), str))
        if re.search(r"\bownership\b", text, re.I) and re.search(r"\b(?:error\w*|fail\w*)\b", text, re.I):
            matches.append({"unit": unit, "doc_text": text, "doc_sha256": hashlib.sha256(text.encode()).hexdigest(),
                            "status": "lexical-match-only; source admission and historical exposure pending"})
    report = {"source_functions": len(units), "source_files": len(files),
              "excluded_parser_files": parent_report["failures"],
              "lexical_matches": len(matches), "inspection_budget": 12,
              "inspected_slice_count": min(12, len(matches)),
              "independent_test_eligible": False, "effectiveness_run": False,
              "selection": "unit ID ascending, no similarity or proposal scores",
              "parent_report_sha256": sha(parent / "report.json")}
    (run / "matches.json").write_text(json.dumps(matches, indent=2) + "\n")
    (run / "inspection-slice.json").write_text(json.dumps(matches[:12], indent=2) + "\n")
    (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "excluded_parser_files"}, indent=2))
    for row in matches[:12]:
        unit = row["unit"]
        print(unit["id"], unit["path"], unit["name"], unit["start_line"])


if __name__ == "__main__":
    main()
