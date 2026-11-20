"""Freeze source-bound synthetic controls and run the unmodified RX test module."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile

from check_event_accounting import evaluate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "research/protocols/event-accounting-v1.json"
    protocol = json.loads(protocol_path.read_text())
    run = root / "research/evidence/runs/2026-11-16-event-accounting-01"
    run.mkdir(exist_ok=False)
    for path, name in [(protocol_path, "protocol.json"), (Path(__file__), "runner.py"), (root / "scripts/check_event_accounting.py", "evaluator.py")]:
        shutil.copy2(path, run / name)
    source = Path("/tmp/xkernel-pagecache-budget-01").resolve()
    parent = root / "research/evidence/runs/2026-11-16-pagecache-disk-01"
    original = json.loads((root / "research/evidence/runs/2026-11-16-pagecache-original-01/report.json").read_text())
    require_hash = original["source_archive_sha256"]
    assert digest(source / "source.tar") == require_hash
    assert digest(source / ".config") == digest(parent / "output.config")
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile():
                assert (source / member.name).read_bytes() == archive.extractfile(member).read(), member.name
        for name, path in protocol["sources"].items():
            (run / name).write_bytes(archive.extractfile(path).read())
    registry = {}
    for entity, filename, unit, events in [
        ("pagecache::submit_cache_pages", "pagecache.rs", "folio", {"handoff":"before submit(batch)", "accepted":"callback returned Ok"}),
        ("knet::Router::drain_rx_budgeted_into", "router.rs", "rx_work_item", {"driver_received":"driver recv succeeded; not necessarily poll success", "poll_consumed":"poll returned Ok(RxPoll::Consumed), including None", "poll_error":"poll returned Err, including recycling failure", "ip_emitted":"an IP packet was appended"}),
    ]:
        registry[entity] = {"source":filename,"sha256":digest(run / filename),"revision":protocol["revision"],"unit":unit,"events":events,"binding_authority":"researcher_source_transcription"}
    write(run / "registry.json", registry)
    contracts = {}
    for entity, binding in registry.items():
        is_pagecache = entity.startswith("pagecache")
        contracts[entity] = {"schema":"event-accounting/1","entity":entity,"revision":binding["revision"],"source_sha256":binding["sha256"],"unit":binding["unit"],"charge_event":"handoff" if is_pagecache else "poll_consumed","representation":"remaining" if is_pagecache else "spent","boundary":"call_return"}
    def record(entity, limit, observed, phases):
        return {"entity":entity,"unit":registry[entity]["unit"],"limit":limit,"observed":observed,"boundary":"call_return","complete":True,"exclusive":True,"credits":False,"events":[{"id":str(index),"phase":phase,"quantity":1} for index, phase in enumerate(phases)],"provenance":"synthetic_source_control"}
    pagecache, network = list(registry)
    cases = []
    def add(identity, entity, evidence, expected):
        cases.append({"id":identity,"contract":copy.deepcopy(contracts[entity]),"record":evidence,"expected_status":expected})
    add("pagecache_handoff", pagecache, record(pagecache, 2, 0, ["handoff", "accepted", "handoff"]), "consistent_record")
    add("pagecache_accept_mutant", pagecache, record(pagecache, 2, 1, ["handoff", "accepted", "handoff"]), "counterexample_record")
    add("rx_drop", network, record(network, 1, 1, ["driver_received", "poll_consumed"]), "consistent_record")
    add("rx_deliver", network, record(network, 1, 1, ["driver_received", "poll_consumed", "ip_emitted"]), "consistent_record")
    add("rx_recycle_error", network, record(network, 4, 0, ["driver_received", "poll_error"]), "consistent_record")
    cases.append(copy.deepcopy(cases[-1])); cases[-1].update(id="rx_wrong_phase", expected_status="counterexample_record")
    cases[-1]["contract"]["charge_event"] = "driver_received"
    for identity, expected in [("missing_event_coverage","unknown"),("wrong_unit","rejected"),("duplicate_event_id","rejected"),("credit_scope","unknown"),("wrong_source","rejected"),("negative_quantity","rejected")]:
        case = copy.deepcopy(cases[0]); case.update(id=identity,expected_status=expected)
        if identity == "missing_event_coverage": case["record"]["complete"] = False
        elif identity == "wrong_unit": case["record"]["unit"] = "byte"
        elif identity == "duplicate_event_id": case["record"]["events"][1]["id"] = "0"
        elif identity == "credit_scope": case["record"]["credits"] = True
        elif identity == "wrong_source": case["contract"]["source_sha256"] = "0" * 64
        elif identity == "negative_quantity": case["record"]["events"][0]["quantity"] = -1
        cases.append(case)
    assert [case["id"] for case in cases] == protocol["controls"]
    write(run / "cases.json", cases)
    repeated = []
    for repeat in range(2):
        results = []
        for case in cases:
            try:
                result = evaluate(case["contract"], case["record"], registry, run)
            except ValueError as error:
                result = {"status":"rejected","reason":str(error)}
            results.append({"id":case["id"],"result":result})
        repeated.append(results)
        write(run / f"results-{repeat}.json", results)
    assert repeated[0] == repeated[1]
    assert all(case["expected_status"] == result["result"]["status"] for case, result in zip(cases, repeated[0]))
    baseline_disk = Path(original["isolated_source"]) / "research-root.ext4"
    parent_report = json.loads((parent / "report.json").read_text())
    assert digest(baseline_disk) == parent_report["disk_sha256_after"]
    shutil.copy2(baseline_disk, source / "research-root.ext4")
    command = protocol["kernel_command"].replace("<source>", str(source))
    environment = dict(os.environ)
    environment.update({"RUSTUP_TOOLCHAIN":"1.95.0","CARGO_NET_OFFLINE":"true","CARGO_BUILD_JOBS":"4","RUSTFLAGS":"","CARGO_ENCODED_RUSTFLAGS":"","GIT_CEILING_DIRECTORIES":"/tmp:/root/.tmp"})
    timed_out = False
    with (run / "kernel.log").open("wb") as log:
        process = subprocess.Popen(command.split(), cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=protocol["kernel_limit_seconds"])
        except subprocess.TimeoutExpired:
            timed_out = True; os.killpg(process.pid, signal.SIGKILL); code = process.wait()
    changed = []
    with tarfile.open(source / "source.tar") as archive:
        for member in archive:
            if member.isfile() and (source / member.name).read_bytes() != archive.extractfile(member).read():
                changed.append(member.name)
    shutil.copy2(source / ".config", run / "output.config")
    write(run / "report.json", {"revision":protocol["revision"],"source_archive_sha256":require_hash,"command":command,"exit_code":code,"timeout":timed_out,"changed_source_files":changed,"config_unchanged":digest(source / ".config") == digest(parent / "output.config"),"synthetic_controls":len(cases),"repeats":2,"kernel_interpretation":"requires_log_review_not_synthetic_trace_validation","artifacts":{path.name:digest(path) for path in run.iterdir()}})
    print(run)


if __name__ == "__main__":
    main()
