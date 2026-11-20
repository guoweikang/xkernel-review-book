"""Independent finite-control and original-suite evidence checks."""
import hashlib
import json
from pathlib import Path
import re


def main():
    run = Path(__file__).resolve().parents[1] / "research/evidence/runs/2026-11-16-event-accounting-01"
    report = json.loads((run / "report.json").read_text())
    for name, digest in report["artifacts"].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == digest, name
    assert not report["changed_source_files"]
    assert report["config_unchanged"]
    first = json.loads((run / "results-0.json").read_text())
    assert first == json.loads((run / "results-1.json").read_text())
    expected = ["consistent_record","counterexample_record","consistent_record","consistent_record","consistent_record","counterexample_record","unknown","rejected","rejected","unknown","rejected","rejected"]
    assert [row["result"]["status"] for row in first] == expected
    assert [row["result"]["expected"] for row in first[:6]] == [0,0,1,1,0,1]
    assert [row["result"]["charged"] for row in first[:6]] == [2,2,1,1,0,1]
    assert all(row["result"]["behavior_truth"] == "not_established" for row in first[:6])
    log = (run / "kernel.log").read_text(errors="replace")
    results = re.findall(r"RESULT (knet::device::ethernet::rx_budget_tests::\S+) \.\.\. (ok|FAILED|ignored)", log)
    summaries = re.findall(r"Test results: (\d+) passed, (\d+) failed, (\d+) ignored, (\d+) total", log)
    status = "not_confirmed_executed"
    if summaries:
        assert len(summaries) == 1
        passed, failed, ignored, total = map(int, summaries[0])
        assert total > 0 and len(results) == len({name for name, value in results}) == total
        assert [sum(value == target for name, value in results) for target in ("ok","FAILED","ignored")] == [passed,failed,ignored]
        assert "Running unit tests with crate filter: knet::device::ethernet::rx_budget_tests" in log
        assert ("=== UNITTEST_STATUS: TESTS_FAILED ===" in log) == bool(failed)
        assert ("=== UNITTEST_STATUS: ALL_TESTS_PASSED ===" in log) == (failed == 0)
        status = "passed" if not failed else "failed"
    focal = ["non_ip_frames_consume_rx_budget_and_recycle_before_returning","dropped_frames_exhaust_budget_and_rotate_to_another_device","zero_rx_budget_does_not_consume_an_ethernet_frame","recycling_failure_ends_rx_without_reading_another_frame"]
    print(json.dumps({"hashes_verified":len(report["artifacts"]),"synthetic_controls":12,"repeat_equal":True,"finite_expected_results":"matched","kernel_status":status,"summaries":summaries,"focal_results":{name:[value for full, value in results if full.endswith("::"+name)] for name in focal},"interpretation":"Original test outcomes do not authenticate the synthetic event records."},indent=2))


if __name__ == "__main__":
    main()
