"""Generate bounded bitfield obligations from declarations, not free-text guesses."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from check_crate_contract import validate

ROOT = Path(__file__).resolve().parents[1]
RUSTC = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc')
DEPENDENCY_SHA = '3ded4057c258ba199e2d26386d3af3780957ecaee6c4ef4041c6b4b8b97c0b06'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(contract, registry, binding):
    validate(contract, registry, ROOT)
    if contract['entity'] != binding['entity'] or contract['conditions'] or contract['kind'] != 'field_update':
        raise ValueError('unsupported obligation mapping')
    statements = []
    for role in ('replace', 'preserve'):
        for field in contract['effect'][role]:
            if field not in binding['fields']:
                raise ValueError('unmapped field')
            mask = binding['fields'][field]
            origin = 'permission_bits' if role == 'replace' else 'bits'
            statements.append(f'            assert_eq!(result & {mask}, {origin} & {mask}, "{role}:{field} bits={{}} permission={{}}", bits, permission_bits);')
    return '''
#[test]
fn declared_obligations() {
    for bits in 0..=u16::MAX {
        for permission_bits in [0, 1, 0o644, 0o755, 0o4000, 0o7777] {
            let permission = NodePermission::from_bits_retain(permission_bits);
            let result = Umode::from_bits(bits).with_permission(permission).bits();
''' + '\n'.join(statements) + '''
        }
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    work = ROOT / '.build/contract-obligations' / args.run_id
    work.mkdir(parents=True)
    parent = ROOT / 'research/evidence/runs/2026-11-16-crate-contract-01'
    report = json.loads((parent / 'report.json').read_text())
    for name in ('cases.json', 'registry.json'):
        if sha(parent / name) != report['artifact_sha256'][name]:
            raise ValueError('parent input changed')
    cases = json.loads((parent / 'cases.json').read_text())
    declarations = {case['id']: case['contract'] for case in cases if case['id'] in ('role', 'well_formed_role_swap')}
    registry = json.loads((parent / 'registry.json').read_text())
    entity = declarations['role']['entity']
    binding = {'entity': entity, 'fields': {'permission_bits': 'PERMISSION_MASK', 'file_type_bits': 'NODE_TYPE_MASK'},
               'replacement_input': 'raw NodePermission bits projected by each field mask',
               'preserved_input': 'original Umode bits', 'method': 'Umode::with_permission',
               'provenance': 'researcher supplied mapping, not compiler inference'}
    source = (ROOT / registry[entity]['source']).read_text()
    begin = source.index('/// Filesystem node type values.')
    end = source.index('/// What a completed unlink/rmdir removed')
    original = source[begin:end]
    expression = 'Self((self.0 & NODE_TYPE_MASK) | (permission.bits() & PERMISSION_MASK))'
    if original.count(expression) != 1:
        raise ValueError('unexpected source identity')
    bodies = {'original': original, 'drop_preserved_type': original.replace(expression, 'Self(permission.bits() & PERMISSION_MASK)')}
    controls = []
    missing = copy.deepcopy(declarations['role'])
    missing['effect']['preserve'] = []
    unknown = copy.deepcopy(declarations['role'])
    unknown['effect']['preserve'] = ['unmapped_bits']
    for name, value in [('missing_preserve', missing), ('unmapped_field', unknown)]:
        controls.append({'id': name, 'contract': value, 'expect': 'reject_before_execution'})
    for name, value in [('declarations.json', declarations), ('registry.json', registry), ('binding.json', binding), ('controls.json', controls)]:
        (folder / name).write_text(json.dumps(value, indent=2) + '\n')
    for declaration, contract in declarations.items():
        assertions = generate(contract, registry, binding)
        for variant, body in bodies.items():
            (folder / f'{declaration}-{variant}.rs').write_text(body + assertions)
    cache = next(Path('/root/.cargo/registry/cache').glob('*/bitflags-2.13.2.crate'))
    if sha(cache) != DEPENDENCY_SHA:
        raise ValueError('dependency hash mismatch')
    protocol = {'design': '2 declarations x 2 bodies x debug/release x 2 execution repeats; no production modification',
                'expected': 'Only role+original passes; other three cells fail generated assertions; invalid mappings rejected before compile.',
                'domain': 'all 65536 initial u16 states times six declared permission values; not all input permissions',
                'scope': 'Extracted original methods and one destructive mutant; binding is manual; no kernel integration or configuration proof.',
                'replacement_semantics': binding['replacement_input'],
                'stop': 'All 16 executions and two rejection controls; preserve failures, no result-driven rule changes',
                'dependency_sha256': DEPENDENCY_SHA, 'source_sha256': registry[entity]['sha256'],
                'source_slice': [begin, end], 'rustc': subprocess.check_output([str(RUSTC), '-Vv']).decode()}
    (folder / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    for path in [Path(__file__), ROOT / 'scripts/check_crate_contract.py']:
        shutil.copy2(path, folder / path.name)
    (folder / 'frozen.json').write_text(json.dumps({path.name: sha(path) for path in sorted(folder.iterdir())}, indent=2) + '\n')
    rejected = []
    for control in controls:
        try:
            generate(control['contract'], registry, binding)
        except ValueError as error:
            rejected.append({'id': control['id'], 'reason': str(error)})
        else:
            raise AssertionError('invalid mapping accepted')
    (folder / 'rejections.json').write_text(json.dumps(rejected, indent=2) + '\n')
    with tarfile.open(cache) as archive:
        archive.extractall(work, filter='data')
    commands = []

    def execute(name, command):
        try:
            result = subprocess.run([str(part) for part in command], capture_output=True, timeout=90)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = 124, error.stdout or b'', error.stderr or b''
        (folder / f'{name}.stdout').write_bytes(stdout)
        (folder / f'{name}.stderr').write_bytes(stderr)
        commands.append({'name': name, 'command': [str(part) for part in command], 'returncode': code})
        (folder / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return code

    assert execute('dependency', [RUSTC, '--edition=2021', '--crate-name', 'bitflags', '--crate-type=rlib',
                                 work / 'bitflags-2.13.2/src/lib.rs', '-o', work / 'libbitflags.rlib']) == 0
    observations = []
    for mode in ('debug', 'release'):
        for declaration in declarations:
            for variant in bodies:
                name = f'{mode}-{declaration}-{variant}'
                command = [RUSTC, '--edition=2024', '--test', folder / f'{declaration}-{variant}.rs',
                           '--extern', 'bitflags=' + str(work / 'libbitflags.rlib'), '-o', work / name]
                if mode == 'release':
                    command.append('-O')
                assert execute(name + '-compile', command) == 0
                expected = 0 if declaration == 'role' and variant == 'original' else 101
                for repeat in (1, 2):
                    identity = name + f'-{repeat}'
                    code = execute(identity, [work / name, '--test-threads=1'])
                    output = (folder / f'{identity}.stdout').read_text()
                    passed = code == expected and ('1 passed; 0 failed' if expected == 0 else '0 passed; 1 failed') in output
                    observations.append({'id': identity, 'declaration': declaration, 'variant': variant,
                                         'mode': mode, 'repeat': repeat, 'expected_returncode': expected,
                                         'returncode': code, 'matched_expectation': passed})
    result = {'success': all(row['matched_expectation'] for row in observations), 'observations': observations,
              'rejected_inputs': rejected, 'sharing': 'unknown', 'optimization_benefit': 'unverified',
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir())}}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'success': result['success'], 'executions': len(observations), 'rejections': len(rejected)}))
    if not result['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
