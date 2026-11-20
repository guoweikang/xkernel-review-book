"""Verify archived execution evidence without treating build success as tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    report = json.loads((args.run / "report.json").read_text())
    for name, expected in report["artifacts"].items():
        assert hashlib.sha256((args.run / name).read_bytes()).hexdigest() == expected, name
    protocol = json.loads((args.run / "protocol.json").read_text())
    assert report["revision"] == protocol["revision"]
    if protocol["schema"] == "original-kernel-tests/1":
        assert report["locks_before"] == report["locks_after"], "lockfile drift"
        for index, command in enumerate(report["commands"]):
            assert command["command"] == protocol["commands"][index]
        log_path = args.run / "command-1.log"
    else:
        assert protocol["schema"] == "original-kernel-disk-control/1"
        parent = args.run.parent / protocol["parent_run"] / "report.json"
        assert hashlib.sha256(parent.read_bytes()).hexdigest() == report["parent_report_sha256"]
        assert report["configuration_unchanged"]
        assert report["archive_files_checked"] > 0
        assert not report["changed_archive_files"], "source drift"
        log_path = args.run / "run.log"
    log = log_path.read_text(errors="replace") if log_path.exists() else ""
    summaries = re.findall(r"Test results: (\d+) passed, (\d+) failed, (\d+) ignored, (\d+) total", log)
    results = re.findall(r"RESULT (pagecache::\S+) \.\.\. (ok|FAILED|ignored)", log)
    status = "not_confirmed_executed"
    if summaries:
        passed, failed, ignored, total = map(int, summaries[-1])
        assert passed + failed + ignored == total
        assert total > 0
        assert "Running unit tests with crate filter: pagecache" in log
        assert len(results) == total
        assert len({name for name, result in results}) == total
        assert [sum(result == value for name, result in results) for value in ("ok", "FAILED", "ignored")] == [passed, failed, ignored]
        status = "tests_failed" if failed else "tests_passed" if passed else "all_ignored"
        if status == "tests_passed":
            assert "=== UNITTEST_STATUS: ALL_TESTS_PASSED ===" in log
            assert "=== UNITTEST_STATUS: TESTS_FAILED ===" not in log
    names = ["submitted_snapshot_outlives_scan_and_preserves_redirty_and_failed_tail", "rejected_submission_redirties_its_batch_without_ending_prior_io", "completion_borrows_index_until_last_writeback_finishes", "writeback_completion_finishes_without_acquiring_the_content_lock"]
    print(json.dumps({"artifact_hashes_verified":len(report["artifacts"]), "status":status, "summaries":summaries, "focal_results":{name:[result for full_name, result in results if full_name.endswith("::" + name)] for name in names}, "commands":report.get("commands", [{"command":report.get("command"), "exit_code":report.get("exit_code"), "timeout":report.get("timeout")}])}, indent=2))


if __name__ == "__main__":
    main()
