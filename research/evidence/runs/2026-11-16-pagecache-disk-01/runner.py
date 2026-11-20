"""Provide an isolated root disk for an already archived original-harness attempt."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "research/protocols/pagecache-disk-control-v1.json"
    protocol = json.loads(protocol_path.read_text())
    parent = root / "research/evidence/runs" / protocol["parent_run"]
    previous = json.loads((parent / "report.json").read_text())
    source = Path(previous["isolated_source"])
    assert digest(source / "source.tar") == previous["source_archive_sha256"]
    assert digest(source / ".config") == digest(parent / "output.config")
    output = root / "research/evidence/runs/2026-11-16-pagecache-disk-01"
    output.mkdir(exist_ok=False)
    shutil.copy2(protocol_path, output / "protocol.json")
    shutil.copy2(__file__, output / "runner.py")
    disk = source / "research-root.ext4"
    assert not disk.exists()
    with (output / "setup.log").open("wb") as log:
        for template in protocol["setup"]:
            command = template.replace("<isolated-source>", str(source))
            subprocess.run(command.split(), stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    before = digest(disk)
    environment = dict(os.environ)
    environment.update({"RUSTUP_TOOLCHAIN":"1.95.0", "CARGO_NET_OFFLINE":"true", "CARGO_BUILD_JOBS":"4", "RUSTFLAGS":"", "CARGO_ENCODED_RUSTFLAGS":"", "GIT_CEILING_DIRECTORIES":"/tmp"})
    command = protocol["command"].replace("<isolated-source>", str(source))
    timed_out = False
    with (output / "run.log").open("wb") as log:
        process = subprocess.Popen(command.split(), cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=protocol["limits"]["timeout_seconds"])
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    changed = []
    checked = 0
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile():
                checked += 1
                expected = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                if not (source / member.name).is_file() or digest(source / member.name) != expected:
                    changed.append(member.name)
    shutil.copy2(source / ".config", output / "output.config")
    report = {"revision":protocol["revision"], "parent_report_sha256":digest(parent / "report.json"), "command":command, "exit_code":code, "timeout":timed_out, "disk_sha256_before":before, "disk_sha256_after":digest(disk), "archive_files_checked":checked, "changed_archive_files":changed, "configuration_unchanged":digest(source / ".config") == digest(parent / "output.config"), "artifacts":{path.name:digest(path) for path in sorted(output.iterdir())}}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
