import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    work = ROOT / '.build' / args.run
    work.mkdir(exist_ok=False)
    fixture = ROOT / 'research/fixtures/deque-document-witness.rs'
    protocol = ROOT / 'research/protocols/deque-document-witness-v1.json'
    for path, name in ((fixture, 'fixture.rs'), (protocol, 'protocol.json'), (Path(__file__), 'runner.py')):
        shutil.copyfile(path, run / name)
    sysroot = Path(subprocess.check_output(['rustc', '+1.95.0', '--print', 'sysroot'], text=True).strip())
    version = subprocess.check_output(['rustc', '+1.95.0', '-Vv'], text=True)
    libraries = sysroot / 'lib/rustlib/x86_64-unknown-linux-gnu/lib'
    freeze = {'compiler': version, 'fixture': sha(fixture), 'protocol': sha(protocol), 'std_libraries': {path.name: sha(path) for pattern in ('libstd-*', 'liballoc-*') for path in sorted(libraries.glob(pattern))}, 'source_inventory': sha(ROOT / 'research/evidence/runs/2026-11-17-rust-standard-inventory-01/inventory.json')}
    (run / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    executions = []
    reference = None
    for mode, optimization in (('debug', '0'), ('release', '3')):
        binary = work / mode
        command = ['rustc', '+1.95.0', '--edition=2024', '-C', 'opt-level=' + optimization, str(run / 'fixture.rs'), '-o', str(binary)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (run / f'{mode}-build.log').write_text(process.stdout + process.stderr)
        assert process.returncode == 0
        for repeat in (1, 2):
            process = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            name = f'{mode}-{repeat}'
            (run / f'{name}.jsonl').write_text(process.stdout)
            (run / f'{name}.stderr').write_text(process.stderr)
            assert process.returncode == 0
            rows = [json.loads(line) for line in process.stdout.splitlines()]
            assert {(row['direction'], row['length'], row['accept']) for row in rows} == set(itertools.product(('front', 'back'), (0, 1, 3), (False, True)))
            assert len(rows) == 12
            for row in rows:
                expected = [10, 20, 30][:row['length']]
                returned = None
                if expected:
                    endpoint = 0 if row['direction'] == 'front' else len(expected) - 1
                    expected[endpoint] += 100
                    if row['accept']:
                        returned = expected.pop(endpoint)
                assert row['remaining'] == expected and row['returned'] == returned
                assert row['calls'] == int(row['length'] != 0)
            reference = rows if reference is None else reference
            assert rows == reference
            executions.append({'id': name, 'build_command': command, 'binary_sha256': sha(binary), 'cases': len(rows)})
    witnesses = [row for row in reference if row['returned'] is None and row['remaining'] != row['initial']]
    assert len(witnesses) == 4
    report = {'status': 'passed', 'unique_conditions': 12, 'executions': executions, 'none_but_mutated_witnesses': witnesses, 'independent_mechanism_families': 'not_estimated', 'method_effectiveness': 'not_tested', 'artifacts_sha256': {path.name: sha(path) for path in sorted(run.iterdir()) if path.is_file()}}
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:12 conditions x debug/release x2;4 concrete None-with-mutation witnesses; no discovery scoring')


if __name__ == '__main__':
    main()
