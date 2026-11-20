"""Run two bounded original-kernel suites with a fixture-local recorder."""
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile

from check_event_accounting import evaluate
from parse_runtime_accounting import parse, receipt


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "research/protocols/runtime-accounting-trace-v1.json"
    protocol = json.loads(protocol_path.read_text())
    run = root / "research/evidence/runs/2026-11-16-runtime-accounting-01"
    run.mkdir(exist_ok=False)
    source = Path("/tmp/xkernel-pagecache-budget-01").resolve()
    parent = root / "research/evidence/runs/2026-11-16-pagecache-disk-01"
    original = json.loads((root / "research/evidence/runs/2026-11-16-pagecache-original-01/report.json").read_text())
    assert digest(source / "source.tar") == original["source_archive_sha256"]
    assert digest(source / ".config") == digest(parent / "output.config")
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile() and member.name != protocol["test_path"]:
                assert (source / member.name).read_bytes() == archive.extractfile(member).read(), member.name
        before = archive.extractfile(protocol["test_path"]).read().decode()
    after = (source / protocol["test_path"]).read_text()
    start = before.index("fn " + protocol["focal_test"] + "()")
    end = before.index("\n#[def_test]", start)
    changed_end = after.index("\n#[def_test]", start)
    assert before[:start] == after[:start] and before[end:] == after[changed_end:]
    (run / "instrumentation.patch").write_text("".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="original/tests.rs",tofile="instrumented/tests.rs")))
    for path, name in [(protocol_path,"protocol.json"),(Path(__file__),"runner.py"),(root / "scripts/parse_runtime_accounting.py","parser.py"),(root / "scripts/check_event_accounting.py","evaluator.py"),(source / protocol["test_path"],"tests.rs"),(source / protocol["implementation_path"],"implementation.rs"),(source / ".config","config")]:
        shutil.copy2(path, run / name)
    command = protocol["command"].replace("<source>", str(source))
    fixed_env = {"RUSTUP_TOOLCHAIN":"1.95.0","CARGO_NET_OFFLINE":"true","CARGO_BUILD_JOBS":"4","RUSTFLAGS":"","CARGO_ENCODED_RUSTFLAGS":"","GIT_CEILING_DIRECTORIES":"/tmp:/root/.tmp"}
    manifest = {"revision":protocol["revision"],"window":protocol["window"],"implementation_sha256":digest(run / "implementation.rs"),"tests_sha256":digest(run / "tests.rs"),"config_sha256":digest(run / "config"),"protocol_sha256":digest(run / "protocol.json"),"parser_sha256":digest(run / "parser.py"),"command":command,"environment":fixed_env}
    write(run / "identity.json", manifest)
    identity = receipt(manifest)
    generated = source / "mm/pagecache/ut-tests/research-trace-receipt.txt"
    assert not generated.exists()
    generated.write_text(identity + "\n")
    shutil.copy2(generated, run / "compiled-receipt.txt")
    entity = "pagecache::submit_cache_pages"
    registry = {entity:{"source":"implementation.rs","revision":protocol["revision"],"sha256":manifest["implementation_sha256"],"unit":"folio","events":{"handoff":"entry of test-owned callback; actual full-page batch.data length"}}}
    contract = {"schema":"event-accounting/1","entity":entity,"revision":protocol["revision"],"source_sha256":manifest["implementation_sha256"],"unit":"folio","charge_event":"handoff","representation":"remaining","boundary":"call_return"}
    write(run / "registry.json",registry); write(run / "contract.json",contract)
    environment = dict(os.environ); environment.update(fixed_env)
    parent_report = json.loads((parent / "report.json").read_text())
    disk = Path(original["isolated_source"]) / "research-root.ext4"
    assert digest(disk) == parent_report["disk_sha256_after"]
    executions = []
    for repeat in range(protocol["runs"]):
        shutil.copy2(disk, source / "research-root.ext4")
        timed_out = False
        with (run / f"kernel-{repeat}.log").open("wb") as log:
            process = subprocess.Popen(command.split(),cwd=source,env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                code = process.wait(timeout=protocol["timeout_seconds_per_run"])
            except subprocess.TimeoutExpired:
                timed_out = True; os.killpg(process.pid,signal.SIGKILL); code = process.wait()
        binary = source / "target/xkmake/kplat-x86_64/release/kernel.debug.elf"
        execution = {"repeat":repeat,"exit_code":code,"timeout":timed_out,"elf_sha256":digest(binary) if binary.exists() else None}
        try:
            captured = parse((run / f"kernel-{repeat}.log").read_text(errors="replace"),manifest)
            write(run / f"capture-{repeat}.json",captured)
            execution["evaluation"] = evaluate(contract,captured["record"],registry,run)
        except ValueError as error:
            execution["capture_error"] = str(error)
        executions.append(execution)
        write(run / "executions.json",executions)
    controls = []
    if (run / "capture-0.json").exists():
        trace = [line.strip() for line in (run / "kernel-0.log").read_text().splitlines() if "ACCT1" in line]
        for name in protocol["controls"]:
            lines = trace.copy(); claimed = copy.deepcopy(manifest)
            if name == "drop_handoff": del lines[1]
            elif name == "drop_end": lines.pop()
            elif name == "drop_window": lines = []
            elif name == "duplicate_event": lines.insert(2,lines[1])
            elif name == "swap_events": lines[1],lines[2] = lines[2],lines[1]
            elif name == "wrong_receipt": lines = [line.replace(identity,"0"*64) for line in lines]
            elif name == "wrong_manifest_revision": claimed["revision"] = "0"*40
            elif name == "wrong_manifest_config": claimed["config_sha256"] = "0"*64
            elif name == "wrong_window": lines = [line.replace(protocol["window"],"foreign-window") for line in lines]
            elif name == "wrong_page_length": lines[1] = lines[1].replace("handoff 4096","handoff 2048")
            try:
                parse("\n".join(lines),claimed)
                outcome = "unexpected_acceptance"
            except ValueError as error:
                outcome = str(error)
            controls.append({"id":name,"log":lines,"manifest":claimed,"outcome":outcome})
    write(run / "controls.json",controls)
    changed = []
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile():
                expected = after.encode() if member.name == protocol["test_path"] else archive.extractfile(member).read()
                if (source / member.name).read_bytes() != expected: changed.append(member.name)
    write(run / "report.json",{"identity":identity,"executions":executions,"unexpected_source_changes":changed,"config_unchanged":digest(source / ".config")==manifest["config_sha256"],"artifacts":{path.name:digest(path) for path in run.iterdir()}})
    print(run)


if __name__ == "__main__":
    main()
