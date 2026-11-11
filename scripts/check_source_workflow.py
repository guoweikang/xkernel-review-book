"""Regression checks for source-workflow gates; no kernel or model execution."""

from copy import deepcopy
import argparse
import json
from pathlib import Path

from run_source_workflow import ROOT, digest, evaluate
from map_source_modules import evaluate_modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    arguments = parser.parse_args()
    protocol = json.loads((ROOT / "research/protocols/source-units-v1.json").read_text())
    result = json.loads((ROOT / "research/evidence/inventory/2026-11-05-four-crate-units.json").read_text())
    regression = json.loads((ROOT / "research/evidence/inventory/2026-11-05-syn-adapter-v2-check.json").read_text())

    def verify(name, candidate, candidate_regression, expected_gate=None):
        failures = {check["name"] for check in evaluate(protocol, candidate, candidate_regression)
                    if not check["passed"]}
        if (expected_gate is None and failures) or (expected_gate is not None and expected_gate not in failures):
            raise ValueError(f"{name}: unexpected failed gates {failures}")

    verify("baseline", result, regression)
    changed = deepcopy(result)
    changed["commit"] = "0" * 40
    verify("mixed commit", changed, regression, "commit")
    changed = deepcopy(result)
    changed["binary_sha256"] = "0" * 64
    verify("mixed binary", changed, regression, "binary_identity")
    changed = deepcopy(result)
    first = next(iter(changed["files"]))
    changed["files"][first]["status"] = "adapter_failure"
    verify("hidden failure", changed, regression, "failed_files")
    verify("missing failure ledger", changed, regression, "failure_ledger")
    changed = deepcopy(result)
    changed["summary"]["files"] -= 1
    verify("wrong denominator", changed, regression, "file_denominator")
    changed = deepcopy(result)
    units = [unit for record in changed["files"].values() for unit in record["units"]]
    units[1]["snapshot_id"] = units[0]["snapshot_id"]
    verify("duplicate identity", changed, regression, "unique_snapshot_ids")
    changed = deepcopy(result)
    changed["summary"]["functions_with_body"] -= 1
    verify("extraction drift", changed, regression, "regression_count:functions_with_body")
    changed_regression = deepcopy(regression)
    changed_regression["fixtures"].pop(next(iter(changed_regression["fixtures"])))
    verify("missing fixture", result, changed_regression, "fixture_count")
    print("PASS: baseline and 8 negative gate checks")
    if arguments.run:
        directory = arguments.run.resolve()
        report = json.loads((directory / "report.json").read_text())
        if report["status"] != "passed_with_limits" or not report["checks"] or not all(
                check["passed"] for check in report["checks"]):
            raise ValueError("Run did not pass gates")
        for name in ("protocol.json", "inventory.json", "regression.json"):
            if name not in report["artifacts"]:
                raise ValueError(f"Missing required artifact: {name}")
        for name, expected in report["artifacts"].items():
            if Path(name).name != name or digest(directory / name) != expected:
                raise ValueError(f"Artifact checksum mismatch: {name}")
        saved_protocol = json.loads((directory / "protocol.json").read_text())
        saved_inventory = json.loads((directory / "inventory.json").read_text())
        saved_regression = json.loads((directory / "regression.json").read_text())
        if not all(check["passed"] for check in evaluate(saved_protocol, saved_inventory, saved_regression)):
            raise ValueError("Recomputed gates failed")
        if "module_mapping" in saved_protocol:
            if "modules.json" not in report["artifacts"]:
                raise ValueError("Missing module mapping artifact")
            mapping = json.loads((directory / "modules.json").read_text())
            if not all(check["passed"] for check in evaluate_modules(saved_protocol, saved_inventory, mapping)):
                raise ValueError("Recomputed module gates failed")
        print("PASS: archived artifacts and recomputed gates (not an authenticity attestation)")


if __name__ == "__main__":
    main()
