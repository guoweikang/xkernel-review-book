import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


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
    for origin, name in ((ROOT / 'research/fixtures/take-nth-state-witness.rs', 'fixture.rs'), (ROOT / 'research/protocols/take-nth-state-witness-v1.json', 'protocol.json'), (Path(__file__), 'runner.py')):
        shutil.copyfile(origin, run / name)
    inventory = ROOT / 'research/evidence/runs/2026-11-17-rust-standard-inventory-01'
    source_report = json.loads((inventory / 'report.json').read_text())
    archive = ROOT / 'research/evidence' / source_report['archive']
    assert sha(archive) == source_report['archive_sha256']
    records = {row['path']: row for row in json.loads((inventory / 'inventory.json').read_text())}
    paths = ['library/core/src/iter/adapters/take.rs', 'library/core/src/iter/traits/iterator.rs']
    with zipfile.ZipFile(archive) as sources:
        for path in paths:
            assert hashlib.sha256(sources.read(path)).hexdigest() == records[path]['sha256']
    sysroot = Path(subprocess.check_output(['rustc', '+1.95.0', '--print', 'sysroot'], text=True).strip())
    libraries = sysroot / 'lib/rustlib/x86_64-unknown-linux-gnu/lib'
    freeze = {'compiler': subprocess.check_output(['rustc', '+1.95.0', '-Vv'], text=True), 'fixture': sha(run / 'fixture.rs'), 'protocol': sha(run / 'protocol.json'), 'source_archive': sha(archive), 'source_files': [records[path] for path in paths], 'core_std': {path.name: sha(path) for pattern in ('libcore-*', 'libstd-*') for path in sorted(libraries.glob(pattern))}}
    (run / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    expected = {
        ('resumable', 'original'): (None, None, [None]),
        ('resumable', 'scan'): (None, 10, [None, 10]),
        ('finite', 'original'): (20, None, [10, 20]),
        ('finite', 'scan'): (20, None, [10, 20]),
    }
    executions = []
    reference = None
    for mode, level in (('debug', '0'), ('release', '3')):
        binary = work / mode
        command = ['rustc', '+1.95.0', '--edition=2024', '-C', 'opt-level=' + level, str(run / 'fixture.rs'), '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (run / f'{mode}-build.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0
        for repeat in (1, 2):
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            name = f'{mode}-{repeat}'
            (run / f'{name}.jsonl').write_text(result.stdout)
            (run / f'{name}.stderr').write_text(result.stderr)
            assert result.returncode == 0
            rows = [json.loads(line) for line in result.stdout.splitlines()]
            observed = {(row['scenario'], row['arm']): (row['first'], row['follow_up'], row['trace']) for row in rows}
            assert len(rows) == 4 and observed == expected
            reference = rows if reference is None else reference
            assert rows == reference
            executions.append({'id': name, 'build_command': command, 'binary_sha256': sha(binary)})
    report = {'status': 'universal_replacement_refuted_by_one_witness', 'cases_per_execution': 4, 'executions': executions, 'finite_control_matches': True, 'resumable_first_return_matches': True, 'resumable_follow_up_matches': False, 'method_accuracy': None, 'artifacts_sha256': {path.name: sha(path) for path in sorted(run.iterdir()) if path.is_file()}}
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:4 cases x4executions; finite control matches; resumable first None matches but follow-up differs; universal replacement refuted')


if __name__ == '__main__':
    main()
