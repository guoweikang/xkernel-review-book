"""Check frozen edits, then execute one cell of the original-kernel factorial."""
import argparse
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


def expected_files(protocol, source, condition):
    with tarfile.open(source / "source.tar") as archive:
        result = {name:archive.extractfile(name).read().decode() for name in (protocol["implementation_path"], protocol["test_path"])}
    if condition.startswith("accepted-"):
        path = protocol["implementation_path"]
        assert result[path].count(protocol["original_body"]) == 1
        result[path] = result[path].replace(protocol["original_body"], protocol["mutant_body"])
    if condition.endswith("-observed"):
        path = protocol["test_path"]
        start = result[path].index("fn " + protocol["focal_test"] + "()")
        end = result[path].index("\n#[def_test]", start)
        body = result[path][start:end]
        for before, after in protocol["test_changes"]:
            assert body.count(before) == 1
            body = body.replace(before, after)
        result[path] = result[path][:start] + body + result[path][end:]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "research/protocols/pagecache-budget-factorial-v1.json"
    protocol = json.loads(protocol_path.read_text())
    assert args.condition in protocol["conditions"]
    source = args.source.resolve()
    parent = root / "research/evidence/runs" / protocol["parent"]
    parent_report = json.loads((parent / "report.json").read_text())
    original = json.loads((root / "research/evidence/runs/2026-11-16-pagecache-original-01/report.json").read_text())
    assert digest(source / "source.tar") == original["source_archive_sha256"]
    assert digest(source / ".config") == digest(parent / "output.config")
    expected = expected_files(protocol, source, args.condition)
    for name, content in expected.items():
        assert (source / name).read_bytes() == content.encode(), name
    run = root / "research/evidence/runs" / ("2026-11-16-pagecache-budget-" + args.condition)
    run.mkdir(exist_ok=False)
    shutil.copy2(protocol_path, run / "protocol.json")
    shutil.copy2(__file__, run / "runner.py")
    for name in expected:
        shutil.copy2(source / name, run / ("implementation.rs" if name == protocol["implementation_path"] else "tests.rs"))
    baseline_disk = Path(original["isolated_source"]) / "research-root.ext4"
    assert digest(baseline_disk) == parent_report["disk_sha256_after"]
    shutil.copy2(baseline_disk, source / "research-root.ext4")
    command = protocol["command"].replace("<source>", str(source))
    environment = dict(os.environ)
    environment.update({"RUSTUP_TOOLCHAIN":"1.95.0", "CARGO_NET_OFFLINE":"true", "CARGO_BUILD_JOBS":str(protocol["limits"]["cargo_jobs"]), "RUSTFLAGS":"", "CARGO_ENCODED_RUSTFLAGS":"", "GIT_CEILING_DIRECTORIES":"/tmp:/root/.tmp"})
    timed_out = False
    with (run / "run.log").open("wb") as log:
        process = subprocess.Popen(command.split(), cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=protocol["limits"]["seconds_per_condition"])
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    changed = []
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile():
                content = expected.get(member.name)
                correct = content.encode() if content is not None else archive.extractfile(member).read()
                if not (source / member.name).is_file() or (source / member.name).read_bytes() != correct:
                    changed.append(member.name)
    shutil.copy2(source / ".config", run / "output.config")
    report = {"condition":args.condition,"revision":protocol["revision"],"source":str(source),"command":command,"exit_code":code,"timeout":timed_out,"unexpected_source_changes":changed,"configuration_unchanged":digest(source / ".config") == digest(parent / "output.config"),"disk_start_sha256":parent_report["disk_sha256_after"],"parent_report_sha256":digest(parent / "report.json"),"artifacts":{path.name:digest(path) for path in run.iterdir()}}
    (run / "report.json").write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
