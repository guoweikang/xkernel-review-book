"""Run original bitfield methods and two destructive controls; no kernel optimization."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RUSTC = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc')
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'
CRATE_SHA = '3ded4057c258ba199e2d26386d3af3780957ecaee6c4ef4041c6b4b8b97c0b06'


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    evidence = ROOT / 'research/evidence/runs' / args.run_id
    build = ROOT / '.build/role-probes' / args.run_id
    evidence.mkdir()
    work = build / 'work'
    work.mkdir(parents=True)
    seed = ROOT / 'research/evidence/runs/2026-11-12-rust-seeds-01/DEV-DOC-PARAMETER-ROLE'
    card = json.loads((seed / 'card.json').read_text())
    source = (seed / '1-source.rs').read_bytes()
    assert sha(source) == card['members'][0]['source_sha256']
    lock = subprocess.check_output(['git', '-C', str(args.repo), 'show', REVISION + ':Cargo.lock'])
    assert CRATE_SHA.encode() in lock
    cache = next(Path('/root/.cargo/registry/cache').glob('*/bitflags-2.13.2.crate'))
    assert sha(cache.read_bytes()) == CRATE_SHA
    with tarfile.open(cache) as archive:
        archive.extractall(work, filter='data')
    template = ROOT / 'research/tools/role-preservation-tests.rs.in'
    text = source.decode()
    begin = text.index('/// Filesystem node type values.')
    end = text.index('/// What a completed unlink/rmdir removed')
    original = text[begin:end]
    mutations = {
        'original': original,
        'drop_type': original.replace('Self((self.0 & NODE_TYPE_MASK) | (permission.bits() & PERMISSION_MASK))', 'Self(permission.bits() & PERMISSION_MASK)'),
        'drop_permission': original.replace('Self(((node_type as u16) << NODE_TYPE_SHIFT) | (self.0 & PERMISSION_MASK))', 'Self((node_type as u16) << NODE_TYPE_SHIFT)')
    }
    assert len(set(mutations.values())) == 3
    for name, content in mutations.items():
        (work / (name + '.rs')).write_text(content + '\n' + template.read_text())
        shutil.copy2(work / (name + '.rs'), evidence / (name + '.rs'))
    (evidence / 'source.rs').write_bytes(source)
    shutil.copy2(template, evidence / template.name)
    shutil.copy2(__file__, evidence / 'runner.py')
    namespace = ROOT / 'scripts/scc_namespace.sh'
    shutil.copy2(namespace, evidence / namespace.name)
    manifest = {'revision': REVISION, 'rustc': subprocess.check_output([str(RUSTC), '-Vv']).decode(),
                'source_sha256': sha(source), 'source_slice_character_offsets': [begin, end],
                'dependency': {'name': 'bitflags', 'version': '2.13.2', 'sha256': CRATE_SHA,
                               'url': 'https://static.crates.io/crates/bitflags/bitflags-2.13.2.crate', 'features': 'no optional features'},
                'design': 'original and two destructive mutants, debug/release; original passes, mutant tests must fail',
                'scope': 'original extracted NodeType/NodePermission/Umode block; unrelated imports and following types omitted; no kernel build',
                'budget': {'commands_timeout_seconds': 90, 'execution_timeout_seconds': 60, 'test_runs': 6},
                'cases': {'permission_states': 65536 * 6, 'type_states': 65536 * 8, 'limitations': 'not all new permission values or integration configurations'},
                'input_sha256': {path.name: sha(path.read_bytes()) for path in evidence.iterdir() if path.is_file()}}
    (evidence / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    results = []

    def execute(command, name):
        try:
            completed = subprocess.run([str(part) for part in command], capture_output=True, timeout=90)
            code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = 124, error.stdout or b'', error.stderr or b''
        (evidence / (name + '.stdout')).write_bytes(stdout)
        (evidence / (name + '.stderr')).write_bytes(stderr)
        results.append({'name': name, 'command': [str(part) for part in command], 'returncode': code})
        (evidence / 'commands.json').write_text(json.dumps(results, indent=2) + '\n')
        return code

    assert execute([RUSTC, '--edition=2021', '--crate-name', 'bitflags', '--crate-type=rlib',
                    work / 'bitflags-2.13.2/src/lib.rs', '-o', work / 'libbitflags.rlib'], 'dependency-compile') == 0
    for mode in ('debug', 'release'):
        for variant in mutations:
            name = mode + '-' + variant
            command = [RUSTC, '--edition=2024', '--test', work / (variant + '.rs'),
                       '--extern', 'bitflags=' + str(work / 'libbitflags.rlib'), '-o', work / name]
            if mode == 'release':
                command += ['-O']
            assert execute(command, name + '-compile') == 0
            command = ['timeout', '60', 'unshare', '--user', '--map-root-user', '--mount', '--pid', '--fork', '--net', '--ipc', '--uts',
                       'bash', namespace, build / (name + '-root'), work, ROOT / '.tools/scc-smoke',
                       '/work/' + name, '--test-threads=1']
            code = execute(command, name)
            assert code == (0 if variant == 'original' else 101), (name, code)
            output = (evidence / (name + '.stdout')).read_text()
            assert ('3 passed; 0 failed' if variant == 'original' else '1 passed; 2 failed') in output
    report = {'passed': True, 'tests_executed': 6, 'original_passes': 2, 'expected_mutant_failures': 4,
              'scope': manifest['scope'], 'effectiveness_score': None,
              'artifact_sha256': {path.name: sha(path.read_bytes()) for path in evidence.iterdir() if path.is_file()}}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}))


if __name__ == '__main__':
    main()
