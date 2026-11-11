"""Run the versioned source-unit protocol with fail-closed gates and evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from inventory_rust_units import inventory
from map_source_modules import evaluate_modules, map_modules


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "research/tools/rust-syntax-probe/Cargo.toml"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def evaluate(protocol, result, regression):
    checks = []

    def check(name, actual, expected, passed=None):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected if passed is None else passed})

    check("commit", result["commit"], protocol["commit"])
    check("regression_commit", regression["commit"], protocol["commit"])
    check("binary_identity", result["binary_sha256"], regression["binary_sha256"])
    check("package_scope", sorted(result["packages"]), sorted(protocol["packages"]))
    check("fixture_count", len(regression["fixtures"]), protocol["gates"]["expected_fixture_count"])
    failures = sum(record["status"] != "parsed_by_syn" for record in result["files"].values())
    maximum = protocol["gates"]["max_failed_files"]
    check("failed_files", failures, maximum, failures <= maximum)
    check("failure_ledger", sorted(result["failures"]), sorted(
        path for path, record in result["files"].items() if record["status"] != "parsed_by_syn"))
    check("file_denominator", result["summary"]["files"], len(result["files"]))
    identities = [unit["snapshot_id"] for record in result["files"].values() for unit in record["units"]]
    check("unique_snapshot_ids", len(identities), len(set(identities)))
    for field, expected in protocol["gates"]["expected_summary"].items():
        check(f"regression_count:{field}", result["summary"][field], expected)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "research/protocols/source-units-v2.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("Output directory already exists; use a new run directory (no overwrites)")
    report = {"schema": "source-workflow-run/1", "started_utc": datetime.now(timezone.utc).isoformat(),
              "status": "execution_failed", "steps": [], "checks": [], "inputs": {}, "artifacts": {}}

    def run(name, command, timeout=300, env=None):
        log = output / f"{name}.log"
        step = {"name": name, "command": [str(part) for part in command], "log": log.name}
        report["steps"].append(step)
        with log.open("w") as stream:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=timeout)
        step["exit_code"] = process.returncode
        if process.returncode:
            raise RuntimeError(f"{name} failed (exit {process.returncode}); see {log.name}")

    code = 2
    try:
        protocol = json.loads(args.config.read_text())
        save(output / "protocol.json", protocol)
        if protocol["schema"] != "source-unit-protocol/1" or not re.fullmatch(r"[0-9a-f]{40}", protocol["commit"]):
            raise ValueError("Protocol must use supported schema and full commit SHA")
        if protocol["toolchain"] != "1.95.0":
            raise ValueError("This runner is validated only with toolchain 1.95.0")
        roots = protocol["packages"]
        if not roots or len(set(roots)) != len(roots) or any(
                not isinstance(root, str) or not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", root)
                for root in roots):
            raise ValueError("Invalid or duplicate physical package roots")
        prior = (ROOT / protocol["prior"]).resolve()
        if not prior.is_relative_to(ROOT) or digest(prior) != protocol["prior_sha256"]:
            raise ValueError("Prior evidence path/hash mismatch")
        if json.loads(prior.read_text())["commit"] != protocol["commit"]:
            raise ValueError("Prior evidence uses another commit")
        source_paths = [Path(__file__).resolve(), *(ROOT / "scripts" / name for name in
                        ("inventory_rust_units.py", "check_syn_probe.py", "probe_rust_units.py",
                         "audit_facts_sample.py", "check_source_workflow.py", "map_source_modules.py")),
                        ROOT / MANIFEST, ROOT / "research/tools/rust-syntax-probe/Cargo.lock",
                        ROOT / "research/tools/rust-syntax-probe/src/main.rs", prior,
                        ROOT / "research/evidence/inventory/2026-11-05-four-crate-units.json",
                        ROOT / "research/evidence/inventory/2026-11-05-syn-adapter-v2-check.json"]
        if "module_mapping" in protocol:
            if protocol["module_mapping"]["rules"] != "tracked-file-candidates/1":
                raise ValueError("Unsupported module mapping rules")
            source_paths.extend(ROOT / "scripts" / name for name in
                                ("map_source_modules.py", "check_module_mapping.py"))
        report["inputs"] = {str(path.relative_to(ROOT)): digest(path) for path in source_paths}
        report["protocol_sha256"] = digest(output / "protocol.json")
        report["known_limits"] = protocol["known_limits"]
        report["python_version"] = sys.version
        repo = args.repo.resolve()
        run("source-preflight", ["git", "-C", str(repo), "cat-file", "-e", protocol["commit"] + "^{commit}"])
        run("rust-version", ["rustup", "run", "1.95.0", "rustc", "--version", "--verbose"])
        run("cargo-version", ["cargo", "+1.95.0", "--version"])
        run("gate-self-check", [sys.executable, "scripts/check_source_workflow.py"])
        target = ROOT / ".build/source-workflow-target"
        env = {**os.environ, "CARGO_TARGET_DIR": str(target)}
        run("build", ["cargo", "+1.95.0", "build", "--offline", "--locked", "--manifest-path", MANIFEST], env=env)
        run("format", ["cargo", "+1.95.0", "fmt", "--manifest-path", MANIFEST, "--", "--check"])
        binary = target / "debug/rust-syntax-probe"
        if "module_mapping" in protocol:
            run("module-regression", [sys.executable, "scripts/check_module_mapping.py", "--binary", str(binary)])
        run("regression", [sys.executable, "scripts/check_syn_probe.py", "--binary", str(binary),
                           "--repo", str(repo), "--prior", str(prior), "--output", str(output / "regression.json")])
        regression = json.loads((output / "regression.json").read_text())
        result = inventory(repo, protocol["commit"], binary, sorted(roots))
        save(output / "inventory.json", result)
        report["summary"] = result["summary"]
        report["checks"] = evaluate(protocol, result, regression)
        if "module_mapping" in protocol:
            mapping = map_modules(repo, result)
            save(output / "modules.json", mapping)
            report["module_summary"] = mapping["summary"]
            report["checks"].extend(evaluate_modules(protocol, result, mapping))
        report["checks"].append({"name": "input_files_unchanged",
                                 "passed": all(digest(ROOT / path) == expected
                                               for path, expected in report["inputs"].items())})
        passed = all(check["passed"] for check in report["checks"])
        report["status"] = "passed_with_limits" if passed else "gate_failed"
        code = 0 if passed else 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report["artifacts"] = {path.name: digest(path) for path in sorted(output.iterdir())
                               if path.is_file() and path.name != "report.json"}
        save(output / "report.json", report)
    print(json.dumps({"status": report["status"], "report": str(output / "report.json")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
