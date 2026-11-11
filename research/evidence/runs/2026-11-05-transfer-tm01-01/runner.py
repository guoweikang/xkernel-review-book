import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUSTC = '/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc'
SOURCES = {
    "STARRY": ("2026-11-05-starry-transfer-01/sources/kernel/src/syscall/fs/io.rs",
               "ccbc859f0a8e12f77f0f60bf6483f779dff5f9edab38babb5aeb8dfc765afe76",
               "enum SendFile {", "pub fn sys_sendfile("),
    "XKERNEL": ("2026-11-05-xkernel-transfer-01/sources/fs/kvfs/src/transfer.rs",
                "f5e4829a2a3b5faa26f832d927eed870bdb9288daf00befa7ee89284383ce2ff",
                "enum Step {", "/// Transfers up to `len` bytes"),
}


def main():
    parser = argparse.ArgumentParser(description="TM01 extracted source with controlled positioned I/O")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("Invalid run ID")
    run = ROOT / '.build/transfer' / args.run_id
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    if run.exists() or evidence.exists():
        parser.error("Run already exists")
    harness = (ROOT / 'research/tools/transfer-probe.rs.in').read_text()
    snippets = {}
    provenance = {}
    for name, (path, checksum, start, end) in SOURCES.items():
        content = (ROOT / 'research/evidence/runs' / path).read_bytes()
        if hashlib.sha256(content).hexdigest() != checksum:
            raise ValueError("Source changed")
        source = content.decode()
        if source.count(start) != 1 or source.count(end) != 1:
            raise ValueError("Ambiguous extraction")
        begin = source.index(start)
        snippet = source[begin:source.index(end, begin)]
        snippets[name] = snippet
        provenance[name] = {"source": path, "source_sha256": checksum,
                            "start_line": source[:begin].count('\n') + 1,
                            "snippet_sha256": hashlib.sha256(snippet.encode()).hexdigest()}
        harness = harness.replace('@@' + name + '@@', snippet)
    work = run / 'work'
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    for name, snippet in snippets.items():
        (evidence / (name.lower() + '.rs')).write_text(snippet)
    shutil.copy2(__file__, evidence / 'runner.py')
    shutil.copy2(ROOT / 'scripts/scc_namespace.sh', evidence / 'namespace.sh')
    (evidence / 'rustc.txt').write_bytes(subprocess.check_output([RUSTC, '-Vv']))
    report = {"passed": False, "scope": "TM01 Offset variant and local file-pair positions with test doubles",
              "provenance": provenance, "commands": [], "kernel_integration": "not_run", "negative_control": "not_run"}

    def execute(command, log):
        report['commands'].append(command)
        with (evidence / log).open('w') as output:
            return subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=90).returncode

    def build_and_run(name, content, arguments):
        (work / (name + '.rs')).write_text(content)
        (evidence / (name + '.rs')).write_text(content)
        compile_code = execute([RUSTC, '--edition=2024', '--test', str(work / (name + '.rs')), '-o', str(work / name)], name + '-compile.log')
        if compile_code != 0:
            raise ValueError(name + ' failed to compile')
        command = ['timeout', '60', 'unshare', '--user', '--map-root-user', '--mount', '--pid', '--net', '--ipc', '--uts', '--fork',
                   'bash', str(ROOT / 'scripts/scc_namespace.sh'), str(run / (name + '-root')), str(work),
                   str(ROOT / '.tools/scc-smoke'), '/work/' + name, '--test-threads=1', '--nocapture', *arguments]
        return execute(command, name + '.log')

    try:
        if build_and_run('probe', harness, []) != 0:
            raise ValueError('Observation/control assertions failed')
        negative = harness.replace('check_transfer(true, 3, 0, 8)', 'check_transfer(true, 3, 3, 8)')
        if negative == harness:
            raise ValueError('Negative control unchanged')
        code = build_and_run('negative', negative, ['starry_short_write_observation', '--exact'])
        log = (evidence / 'negative.log').read_text()
        if code != 101 or 'assertion `left == right` failed' not in log or '1 failed' not in log:
            raise ValueError('Incorrect equal-count expectation not rejected')
        report['negative_control'] = 'equal_completed_count_expectation_rejected'
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({"passed": report['passed'], "error": report.get('error'), "evidence": str(evidence)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
