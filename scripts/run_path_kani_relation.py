#!/usr/bin/env python3
"""Run a bounded relational harness on the previously archived path candidate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if Path(args.run).name != args.run:
        parser.error("run must be a single directory name")
    evidence = root / "research/evidence/runs"
    controls = evidence / "2026-11-17-kani-recovery-01/controls/report.json"
    if not json.loads(controls.read_text())["all_matched"]:
        raise RuntimeError("official control gate has not passed")
    protocol_path = root / "research/protocols/path-kani-relation-v1.json"
    protocol = json.loads(protocol_path.read_text())
    parent = evidence / protocol["parent_run"]
    parent_manifest = json.loads((parent / "manifest.json").read_text())
    run = evidence / args.run
    work = root / ".build" / args.run
    run.mkdir(exist_ok=False)
    work.mkdir(exist_ok=False)
    inputs = {}
    for arm in ("original", "candidate"):
        source = parent / arm / "src/path.rs"
        assert digest(source) == parent_manifest["files"][f"{arm}/src/path.rs"]
        shutil.copyfile(source, run / f"{arm}.rs")
        shutil.copyfile(source, work / f"{arm}.rs")
        inputs[f"{arm}.rs"] = digest(source)
    fixture = root / "research/fixtures/path-kani-relation.rs"
    shutil.copyfile(fixture, run / "harness.rs")
    shutil.copyfile(fixture, work / "harness.rs")
    shutil.copyfile(protocol_path, run / "protocol.json")
    shutil.copyfile(Path(__file__), run / "runner.py")
    inputs.update({name: digest(run / name) for name in ("harness.rs", "protocol.json", "runner.py")})
    environment = dict(os.environ, KANI_HOME=str(root / ".build/kani-home"))
    environment.pop("RUSTFLAGS", None)
    environment.pop("CARGO_ENCODED_RUSTFLAGS", None)
    command = ["timeout", "--kill-after=5s", str(protocol["budget"]["attempt_seconds"]),
               str(root / ".build/kani-installer-0.68.0/bin/kani"),
               str(work / "harness.rs"), "--harness", "check_path_methods"]
    manifest = {"inputs": inputs, "parent_manifest_sha256": digest(parent / "manifest.json"),
                "control_report_sha256": digest(controls), "command": command,
                "working_directory": str(work), "scope": protocol,
                "toolchain": (root / ".build/kani-home/kani-0.68.0/rustc-version").read_text()}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def limit_memory():
        limit = protocol["budget"]["address_space_bytes"]
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    started = time.monotonic()
    with (run / "verification.log").open("wb") as log:
        result = subprocess.run(command, cwd=work, env=environment, stdout=log,
                                stderr=subprocess.STDOUT, preexec_fn=limit_memory)
    raw = (run / "verification.log").read_text(errors="replace")
    status = "unresolved-see-log"
    if result.returncode == 0 and "VERIFICATION:- SUCCESSFUL" in raw:
        status = "bounded-obligations-successful"
    elif result.returncode in (124, 137):
        status = "resource-timeout"
    elif "VERIFICATION:- FAILED" in raw:
        status = "verification-failure-requires-inspection"
    report = {"exit": result.returncode, "seconds": time.monotonic() - started,
              "status": status, "log_sha256": digest(run / "verification.log"),
              "inputs_unchanged": all(digest(run / name) == value for name, value in inputs.items())}
    (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
