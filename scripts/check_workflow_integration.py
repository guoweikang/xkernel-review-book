"""Check workflow exit codes, failure evidence, no-overwrite and artifact integrity."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from run_source_workflow import ROOT, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    arguments = parser.parse_args()
    archive = arguments.run.resolve()
    subprocess.run([sys.executable, str(ROOT / "scripts/check_source_workflow.py"),
                    "--run", str(archive)], check=True)

    def invoke(script, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                              capture_output=True, text=True, timeout=300)

    with tempfile.TemporaryDirectory(prefix="source-workflow-check-") as temporary:
        directory = Path(temporary)
        protocol = json.loads((archive / "protocol.json").read_text())
        protocol["gates"]["expected_summary"]["files"] += 1
        config = directory / "drift.json"
        config.write_text(json.dumps(protocol))
        process = invoke("run_source_workflow.py", "--repo", arguments.repo,
                         "--config", config, "--output", directory / "drift")
        if process.returncode != 1 or json.loads((directory / "drift/report.json").read_text())["status"] != "gate_failed":
            raise ValueError(f"Drift was not rejected with evidence: {process.stdout} {process.stderr}")
        print("PASS: count drift exits 1 and retains failed report")
        process = invoke("run_source_workflow.py", "--repo", directory / "absent",
                         "--output", directory / "preflight")
        if process.returncode != 2 or json.loads((directory / "preflight/report.json").read_text())["status"] != "execution_failed":
            raise ValueError("Missing repository did not produce execution_failed evidence")
        print("PASS: missing repo exits 2 with report")
        before = digest(archive / "report.json")
        process = invoke("run_source_workflow.py", "--repo", arguments.repo, "--output", archive)
        if process.returncode != 2 or digest(archive / "report.json") != before:
            raise ValueError("Existing archive was not protected")
        print("PASS: existing run cannot be overwritten")
        shutil.copytree(archive, directory / "tampered")
        with (directory / "tampered/inventory.json").open("a") as stream:
            stream.write("\n")
        process = invoke("check_source_workflow.py", "--run", directory / "tampered")
        if process.returncode == 0 or "checksum mismatch" not in process.stderr:
            raise ValueError("Changed artifact was not rejected")
        print("PASS: changed artifact rejected by checksum")


if __name__ == "__main__":
    main()
