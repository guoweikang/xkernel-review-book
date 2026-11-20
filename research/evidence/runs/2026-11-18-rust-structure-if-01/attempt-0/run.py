import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import time
import traceback

from check_controls import check_control, validate_tree

RUN = pathlib.Path(__file__).resolve().parent
ROOT = RUN.parents[3]
SOURCE = ROOT / 'research/tools/rust-syntax-probe/src/bin/rust-structure-if-probe.rs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def command(directory, name, argv, environment, source=None, timeout=10):
    started = time.perf_counter()
    result = {'argv': list(map(str, argv)), 'started_unix': time.time()}
    try:
        process = subprocess.run(result['argv'], input=source, cwd=ROOT,
                                 env=environment, capture_output=True, timeout=timeout)
        stdout, stderr = process.stdout, process.stderr
        result['exit_code'] = process.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b'', error.stderr or b''
        result['failure'] = 'timeout'
    result['elapsed_seconds'] = time.perf_counter() - started
    (directory / (name + '.stdout')).write_bytes(stdout)
    (directory / (name + '.stderr')).write_bytes(stderr)
    save(directory / (name + '.command.json'), result)
    return result, stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, required=True, choices=range(2))
    args = parser.parse_args()
    protocol = json.loads((RUN / 'protocol.json').read_text())
    for path, expected in protocol['identity']['hashes'].items():
        assert sha(ROOT / path) == expected, path
    assert len(SOURCE.read_text().splitlines()) <= protocol['budget']['max_lines']
    baseline = ROOT / protocol['baseline_run']
    (RUN / 'reference').mkdir(exist_ok=True)
    for name in ['check_controls.py', 'corpus-context.json', 'summary.json']:
        target = RUN / 'reference' / name
        if not target.exists():
            shutil.copyfile(baseline / name, target)
    if args.attempt:
        assert (RUN / f'attempt-{args.attempt - 1}' / 'result.json').exists()
    directory = RUN / f'attempt-{args.attempt}'
    directory.mkdir()
    for path in [SOURCE, RUN / 'run.py', RUN / 'check_controls.py', RUN / 'protocol.json', RUN / 'extension-checks.json']:
        shutil.copyfile(path, directory / path.name)
    for name in ['Cargo.toml', 'Cargo.lock']:
        shutil.copyfile(ROOT / 'research/tools/rust-syntax-probe' / name, directory / name)
    environment = dict(os.environ, CARGO_TARGET_DIR=str(ROOT / '.build/rust-structure-if-probe'),
                       CARGO_NET_OFFLINE='true', RUSTUP_TOOLCHAIN='1.95.0-x86_64-unknown-linux-gnu')
    save(directory / 'start.json', {'protocol_sha256': sha(RUN / 'protocol.json'),
         'source_sha256': sha(SOURCE), 'python': platform.python_version(),
         'platform': platform.platform(), 'environment': {key: environment[key] for key in
         ['CARGO_TARGET_DIR', 'CARGO_NET_OFFLINE', 'RUSTUP_TOOLCHAIN']},
         'runner_sha256': sha(RUN / 'run.py'), 'tests_sha256': sha(RUN / 'check_controls.py')})
    command(directory, 'cargo-version', ['cargo', '--version'], environment)
    command(directory, 'rustc-version', ['rustc', '--version', '--verbose'], environment)
    build, _ = command(directory, 'build', ['cargo', 'build', '--offline', '--locked', '--manifest-path',
        'research/tools/rust-syntax-probe/Cargo.toml', '--bin', 'rust-structure-if-probe'], environment, timeout=120)
    if build.get('exit_code') != 0:
        save(directory / 'result.json', {'passed': False, 'stage': 'build', 'build': build})
        return
    binary = ROOT / '.build/rust-structure-if-probe/debug/rust-structure-if-probe'
    save(directory / 'binary.json', {'path': str(binary.relative_to(ROOT)), 'sha256': sha(binary)})
    records = []
    for control in protocol['controls']:
        prefix = 'control-' + control['id']
        encoded = control['source'].encode()
        (directory / (prefix + '.rs')).write_bytes(encoded)
        result, stdout = command(directory, prefix, [binary], environment, source=encoded)
        record = {'id': control['id'], 'passed': False, 'source_sha256': hashlib.sha256(encoded).hexdigest()}
        try:
            assert result.get('exit_code') == 0, result
            output = json.loads(stdout)
            check_control(control, output)
            if int(control['id']) <= 12:
                old = json.loads((baseline / 'attempt-0' / (prefix + '.stdout')).read_text())
                assert old == output, 'original control JSON changed'
            record.update(passed=True, status=output['status'], coverage=output['coverage'])
        except Exception:
            record['failure'] = traceback.format_exc()
        records.append(record)
    controls_passed = all(record['passed'] for record in records)
    save(directory / 'control-checks.json', {'passed': controls_passed, 'records': records})
    if not controls_passed:
        save(directory / 'result.json', {'passed': False, 'stage': 'controls'})
        return
    corpus_dir = RUN / 'corpus'
    corpus_dir.mkdir()
    source_records = json.loads((ROOT / 'research/evidence/runs/2026-11-18-common-call-syntax-01/calls.json').read_text())['records']
    by_id = {record['unit_id']: record for record in source_records}
    corpus_results = []
    for unit_id in protocol['identity']['unit_ids']:
        record = by_id[unit_id]
        encoded = record['source_text'].encode()
        assert hashlib.sha256(encoded).hexdigest() == record['source_sha256']
        (corpus_dir / (unit_id + '.rs')).write_bytes(encoded)
        result, stdout = command(corpus_dir, unit_id, [binary], environment, source=encoded)
        evidence = {'unit_id': unit_id, 'source_sha256': record['source_sha256'],
                    'file_source_sha256': record['file_source_sha256'], 'path': record['path'],
                    'range': record['range'], 'original_range': record['original_range'], 'passed': False}
        try:
            assert result.get('exit_code') == 0, result
            output = json.loads(stdout)
            validate_tree(output, record['source_text'])
            evidence.update(passed=True, status=output['status'], coverage=output['coverage'],
                            nodes=len(output['nodes']), occurrences=len(output['occurrences']))
        except Exception:
            evidence['failure'] = traceback.format_exc()
        corpus_results.append(evidence)
    unchanged = all(sha(ROOT / path) == expected for path, expected in protocol['identity']['hashes'].items())
    save(corpus_dir / 'results.json', {'records': corpus_results, 'unit_count': len(corpus_results),
        'selection': 'Same eight frozen IDs and same source bytes as baseline', 'source_binary_attempt': args.attempt})
    save(directory / 'result.json', {'passed': controls_passed and unchanged and all(record['passed'] for record in corpus_results),
        'stage': 'complete', 'controls': len(records), 'corpus_units': len(corpus_results),
        'protected_sources_unchanged': unchanged, 'binary_unchanged': sha(binary) == json.loads((directory / 'binary.json').read_text())['sha256'],
        'protocol_unchanged': sha(RUN / 'protocol.json') == json.loads((directory / 'start.json').read_text())['protocol_sha256']})


if __name__ == '__main__':
    main()
