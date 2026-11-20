"""Check all four frozen cells; report outcomes rather than assume predictions."""
import hashlib
import json
from pathlib import Path
import re


def main():
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "research/protocols/pagecache-budget-factorial-v1.json").read_text())
    runs = root / "research/evidence/runs"
    rows = []
    snapshots = {}
    for condition in protocol["conditions"]:
        run = runs / ("2026-11-16-pagecache-budget-" + condition)
        report = json.loads((run / "report.json").read_text())
        assert report["condition"] == condition
        assert report["revision"] == protocol["revision"]
        assert json.loads((run / "protocol.json").read_text()) == protocol
        assert not report["unexpected_source_changes"]
        assert report["configuration_unchanged"]
        parent = runs / protocol["parent"] / "report.json"
        assert hashlib.sha256(parent.read_bytes()).hexdigest() == report["parent_report_sha256"]
        for name, expected in report["artifacts"].items():
            assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, (condition, name)
        snapshots[condition] = {name:(run / name).read_bytes() for name in ("implementation.rs", "tests.rs")}
        log = (run / "run.log").read_text(errors="replace")
        results = re.findall(r"RESULT (pagecache::\S+) \.\.\. (ok|FAILED|ignored)", log)
        summaries = re.findall(r"Test results: (\d+) passed, (\d+) failed, (\d+) ignored, (\d+) total", log)
        status = "not_confirmed_executed"
        if summaries:
            assert len(summaries) == 1
            passed, failed, ignored, total = map(int, summaries[0])
            assert len(results) == len({name for name, value in results}) == total == 68
            assert [sum(value == expected for name, value in results) for expected in ("ok", "FAILED", "ignored")] == [passed, failed, ignored]
            assert "Running unit tests with crate filter: pagecache" in log
            assert ("=== UNITTEST_STATUS: TESTS_FAILED ===" in log) == bool(failed)
            assert ("=== UNITTEST_STATUS: ALL_TESTS_PASSED ===" in log) == (failed == 0)
            status = "failed" if failed else "passed"
        rows.append({"condition":condition,"status":status,"summary":summaries,"focal_results":[value for name, value in results if name.endswith("::" + protocol["focal_test"])],"failed_tests":[name for name, value in results if value == "FAILED"],"budget_counterexamples":re.findall(r"budget \((\d+)\) == 0 \((\d+)\)", log),"exit_code":report["exit_code"],"timeout":report["timeout"]})
    for dimension, pairs in {
        "implementation.rs":[("original-old","original-observed"),("accepted-old","accepted-observed")],
        "tests.rs":[("original-old","accepted-old"),("original-observed","accepted-observed")],
    }.items():
        for first, second in pairs:
            assert snapshots[first][dimension] == snapshots[second][dimension]
    assert snapshots["original-old"]["implementation.rs"] != snapshots["accepted-old"]["implementation.rs"]
    assert snapshots["original-old"]["tests.rs"] != snapshots["original-observed"]["tests.rs"]
    print(json.dumps({"schema":"budget-factorial-check/1","rows":rows,"identity_and_factor_controls":"passed","limits":"One targeted mutation, one execution per cell; no accuracy or novelty claim."}, indent=2))


if __name__ == "__main__":
    main()
