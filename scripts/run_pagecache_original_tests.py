"""Bounded original-harness attempt, isolated from all existing worktrees."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "research/evidence/runs" / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    protocol_path = root / "research/protocols/pagecache-original-tests-v1.json"
    protocol = json.loads(protocol_path.read_text())
    shutil.copy2(protocol_path, output / "protocol.json")
    shutil.copy2(__file__, output / "runner.py")
    source = Path(tempfile.mkdtemp(prefix="xkernel-pagecache-", dir="/tmp"))
    archive = source / "source.tar"
    subprocess.run(["git", "-C", args.repo, "archive", protocol["revision"], "-o", str(archive)], check=True)
    archive_hash = digest(archive)
    subprocess.run(["tar", "-xf", str(archive), "-C", str(source)], check=True)
    shutil.copy2(source / protocol["config"].split(" copied")[0], source / ".config")
    shutil.copy2(source / ".config", output / "input.config")
    locks = ["Cargo.lock", "xtask/Cargo.lock"]
    before = {name: digest(source / name) for name in locks if (source / name).exists()}
    environment = dict(os.environ)
    environment.update(protocol["environment"])
    environment.update({"RUSTFLAGS":"", "CARGO_ENCODED_RUSTFLAGS":"", "GIT_CEILING_DIRECTORIES":"/tmp"})
    results = []
    for index, command in enumerate(protocol["commands"]):
        limit = protocol["limits"]["configuration_timeout_seconds" if index == 0 else "build_and_run_timeout_seconds"]
        started = time.monotonic()
        with (output / f"command-{index}.log").open("wb") as log:
            process = subprocess.Popen(command.split(), cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            try:
                code = process.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
        results.append({"command":command, "exit_code":code, "timeout":timed_out, "seconds":round(time.monotonic()-started,3)})
        if code != 0:
            break
    after = {name: digest(source / name) for name in locks if (source / name).exists()}
    shutil.copy2(source / ".config", output / "output.config")
    report = {"revision":protocol["revision"], "isolated_source":str(source), "source_archive_sha256":archive_hash, "commands":results, "locks_before":before, "locks_after":after, "lockfiles_unchanged":before == after, "test_outcome":"requires_serial_log_review", "artifacts":{path.name:digest(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
