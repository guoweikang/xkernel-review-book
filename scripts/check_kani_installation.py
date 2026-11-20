#!/usr/bin/env python3
"""Execute the two upstream installation controls, preserving raw results."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run = (root / "research/evidence/runs" / args.run).resolve()
    protocol = json.loads((run / "protocol.json").read_text())
    output = run / "controls"
    output.mkdir(exist_ok=False)
    launcher = root / ".build/kani-installer-0.68.0/bin/kani"
    environment = dict(os.environ, KANI_HOME=str(root / ".build/kani-home"))
    environment.pop("RUSTFLAGS", None)
    environment.pop("CARGO_ENCODED_RUSTFLAGS", None)
    records = []
    for control in protocol["controls"]:
        source = output / (control["id"] + ".rs")
        source.write_text("#[kani::proof]\nfn main() {\n    assert!(" + control["assertion"] + ");\n}\n")
        command = [str(launcher), str(source)]
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=output, env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=protocol["budget"]["each_control_seconds"])
            raw, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            raw, code = error.stdout or b"", 124
        log = output / (control["id"] + ".log")
        log.write_bytes(raw)
        text = raw.decode(errors="replace")
        expected_exit = code == 0 if control["id"] == "true" else code not in (0, 124)
        records.append({"id": control["id"], "command": command, "exit": code,
                        "seconds": time.monotonic() - started,
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "log_sha256": hashlib.sha256(raw).hexdigest(),
                        "expected_marker": control["expected"],
                        "matched": control["expected"] in text and expected_exit})
    report = {"scope": protocol["scope"], "controls": records,
              "all_matched": all(record["matched"] for record in records)}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["all_matched"] else 1)


if __name__ == "__main__":
    main()
