"""Independently check the bounded recorder experiment and suite summaries."""
import hashlib
import json
from pathlib import Path
import re


def main():
    run = Path(__file__).resolve().parents[1] / "research/evidence/runs/2026-11-16-runtime-accounting-01"
    report = json.loads((run / "report.json").read_text())
    for name, expected in report["artifacts"].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    assert not report["unexpected_source_changes"] and report["config_unchanged"]
    manifest = json.loads((run / "identity.json").read_text())
    identity = hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert identity == report["identity"] == (run / "compiled-receipt.txt").read_text().strip()
    for key, name in [("implementation_sha256","implementation.rs"),("tests_sha256","tests.rs"),("config_sha256","config"),("protocol_sha256","protocol.json"),("parser_sha256","parser.py")]:
        assert manifest[key] == hashlib.sha256((run / name).read_bytes()).hexdigest()
    protocol = json.loads((run / "protocol.json").read_text())
    assert manifest["revision"] == protocol["revision"]
    assert len(report["executions"]) == 2
    captures = []
    outcomes = []
    for repeat, execution in enumerate(report["executions"]):
        log = (run / f"kernel-{repeat}.log").read_text(errors="replace")
        results = re.findall(r"RESULT (pagecache::\S+) \.\.\. (ok|FAILED|ignored)",log)
        summaries = re.findall(r"Test results: (\d+) passed, (\d+) failed, (\d+) ignored, (\d+) total",log)
        assert len(summaries) == 1
        passed, failed, ignored, total = map(int,summaries[0])
        assert total == len(results) == len({name for name, value in results}) == 68
        assert [sum(value == target for name,value in results) for target in ("ok","FAILED","ignored")] == [passed,failed,ignored]
        assert "Running unit tests with crate filter: pagecache" in log
        assert failed == 0 and passed == 68 and ignored == 0
        assert "=== UNITTEST_STATUS: ALL_TESTS_PASSED ===" in log and "=== UNITTEST_STATUS: TESTS_FAILED ===" not in log
        assert execution["exit_code"] == 0 and not execution["timeout"]
        tokens = [line.strip().split() for line in log.splitlines() if "ACCT1" in line]
        assert len(tokens) == 6
        assert all(len(row) == 6 and row[:3] == ["ACCT1",identity,protocol["window"]] for row in tokens)
        assert [int(row[3]) for row in tokens] == list(range(6))
        assert [row[4] for row in tokens] == ["begin","handoff","accept","handoff","reject","end"]
        assert [int(row[5]) for row in tokens] == [2,4096,1,4096,1,0]
        captured = json.loads((run / f"capture-{repeat}.json").read_text())
        assert captured["record"]["observed"] == int(tokens[-1][5])
        assert sum(event["quantity"] for event in captured["record"]["events"]) == 2
        assert execution["evaluation"]["expected"] == execution["evaluation"]["observed"] == 0
        assert execution["evaluation"]["status"] == "consistent_record"
        captures.append(captured)
        outcomes.append({"repeat":repeat,"passed":passed,"events":len(tokens),"observed_remaining":int(tokens[-1][5]),"elf_sha256":execution["elf_sha256"]})
    assert captures[0] == captures[1]
    controls = json.loads((run / "controls.json").read_text())
    assert [case["id"] for case in controls] == protocol["controls"]
    expected_errors = ["sequence_gap_duplicate_or_reorder","window_not_closed","expected_window_missing","sequence_gap_duplicate_or_reorder","sequence_gap_duplicate_or_reorder","receipt_mismatch","receipt_mismatch","receipt_mismatch","window_mismatch","full_page_binding_not_established"]
    assert [case["outcome"] for case in controls] == expected_errors
    print(json.dumps({"artifact_hashes_verified":len(report["artifacts"]),"executions":outcomes,"normalized_captures_equal":True,"corruption_controls_rejected":len(controls),"scope":"Fixture-bound real records, not universal instrumentation completeness or attestation."},indent=2))


if __name__ == "__main__":
    main()
