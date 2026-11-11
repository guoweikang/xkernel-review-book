import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVISION = '658544d874297d246064a04910f893bafb320bb1'
RUSTC = '/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc'


def main():
    parser = argparse.ArgumentParser(description='Historical table-only conformance and mutation audit')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        parser.error('Invalid run ID')
    run = ROOT / '.build/bpf-audit' / args.run_id
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    if run.exists() or evidence.exists():
        parser.error('Run exists')
    work = run / 'work'
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    sources = {}
    for path in ['core/kbpf/src/uapi.rs', 'core/kbpf/tests/uapi_conformance.rs', 'xtask/bpf_uapi/gen.py']:
        content = subprocess.check_output(['git', '-C', args.repo, 'show', REVISION + ':' + path])
        (evidence / Path(path).name).write_bytes(content)
        sources[path] = hashlib.sha256(content).hexdigest()
    table = (evidence / 'uapi.rs').read_text()
    tests = (evidence / 'uapi_conformance.rs').read_text()
    variants = {
        'baseline': table,
        'covered_mutation': table.replace('pub const BPF_PROG_TYPE_CGROUP_DEVICE: u32 = 15;', 'pub const BPF_PROG_TYPE_CGROUP_DEVICE: u32 = 99;'),
        'uncovered_mutation': table.replace('pub const BPF_REG_0: u32 = 0;', 'pub const BPF_REG_0: u32 = 99;'),
    }
    if variants['covered_mutation'] == table or variants['uncovered_mutation'] == table:
        raise ValueError('Mutation did not apply')
    if 'BPF_REG_0' in tests:
        raise ValueError('Selected uncovered symbol is referenced by test text')
    report = {'revision': REVISION, 'source_sha256': sources, 'commands': [], 'results': {},
              'scope': 'Original table and test file, minimal kbpf module facade; not full crate, generator or Linux ABI validation', 'passed': False}
    shutil.copy2(__file__, evidence / 'runner.py')
    shutil.copy2(ROOT / 'scripts/scc_namespace.sh', evidence / 'namespace.sh')
    (evidence / 'rustc.txt').write_bytes(subprocess.check_output([RUSTC, '-Vv']))

    def execute(command, log):
        report['commands'].append(command)
        with (evidence / log).open('w') as output:
            return subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=90).returncode

    try:
        for name, content in variants.items():
            directory = work / name
            directory.mkdir()
            (directory / 'uapi.rs').write_text(content)
            (evidence / (name + '-uapi.rs')).write_text(content)
            (directory / 'lib.rs').write_text('pub mod uapi;\n')
            (directory / 'test.rs').write_text(tests)
            library = directory / 'libkbpf.rlib'
            if execute([RUSTC, '--edition=2024', '--crate-name', 'kbpf', '--crate-type', 'rlib', str(directory / 'lib.rs'), '-o', str(library)], name + '-lib.log'):
                raise ValueError('Library compile failed')
            if execute([RUSTC, '--edition=2024', '--test', str(directory / 'test.rs'), '--extern', 'kbpf=' + str(library), '-o', str(directory / 'test')], name + '-compile.log'):
                raise ValueError('Test compile failed')
            command = ['timeout', '60', 'unshare', '--user', '--map-root-user', '--mount', '--pid', '--net', '--ipc', '--uts', '--fork',
                       'bash', str(ROOT / 'scripts/scc_namespace.sh'), str(run / (name + '-root')), str(work),
                       str(ROOT / '.tools/scc-smoke'), '/work/' + name + '/test', '--test-threads=1', '--nocapture']
            report['results'][name] = execute(command, name + '.log')
        report['passed'] = report['results'] == {'baseline': 0, 'covered_mutation': 101, 'uncovered_mutation': 0}
        if 'assertion `left == right` failed' not in (evidence / 'covered_mutation.log').read_text():
            report['passed'] = False
    except Exception as error:
        report['error'] = str(error)
    finally:
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['results']))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
