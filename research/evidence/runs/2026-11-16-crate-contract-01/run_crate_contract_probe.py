"""Freeze and execute schema controls, including well-formed false declarations."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

from check_crate_contract import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid run ID')
    root = Path(__file__).resolve().parents[1]
    folder = root / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    registry = {}
    inputs = {}
    for name, entity in [('role', 'fs/kvfs/src/types.rs::with_permission'),
                         ('command', 'fs/kvfs/src/simple_file.rs::CommandFile::write_iter')]:
        source = Path(f'research/evidence/runs/2026-11-16-rust-srl-inputs-01/{name}-source.txt')
        registry[entity] = {'source': str(source), 'revision': '7e3ac94431a0dbb376d2fc8d85098deeff1bba09',
                            'sha256': hashlib.sha256((root / source).read_bytes()).hexdigest()}
        inputs[name] = {'schema': 'crate-contract/0', 'entity': entity,
                        'revision': registry[entity]['revision'], 'source_sha256': registry[entity]['sha256'],
                        'configuration': {'status': 'unknown', 'expression': None},
                        'responsibility': {'owner': 'kvfs', 'basis': 'declared'},
                        'kind': 'field_update' if name == 'role' else 'callback', 'conditions': [],
                        'effect': {'replace': ['permission_bits'], 'preserve': ['file_type_bits'], 'result': 'new_value'}
                        if name == 'role' else {'target': 'self.write', 'count': 1, 'payload': 'whole',
                                               'after': 'whole_collection', 'on_collection_failure': 'no_callback'}}
    inputs['command']['conditions'] = [{'subject': 'input_length', 'operator': 'gt', 'value': 0},
                                       {'subject': 'input_length', 'operator': 'le', 'value': 4096}]
    cases = [{'id': name, 'contract': value, 'accept': True} for name, value in inputs.items()]

    def altered(identity, base, accept):
        value = copy.deepcopy(inputs[base])
        cases.append({'id': identity, 'contract': value, 'accept': accept})
        return value

    del altered('missing_conditions', 'command', False)['conditions']
    del altered('missing_action', 'command', False)['effect']['target']
    altered('unknown_entity', 'role', False)['entity'] = 'unregistered'
    altered('wrong_revision', 'role', False)['revision'] = '0' * 40
    altered('wrong_source_hash', 'role', False)['source_sha256'] = '0' * 64
    altered('overlap_roles', 'role', False)['effect']['preserve'] = ['permission_bits']
    altered('invalid_operator', 'command', False)['conditions'][0]['operator'] = 'execute'
    altered('boolean_count', 'command', False)['effect']['count'] = True
    altered('invented_confirmation', 'role', False)['confirmed'] = True
    altered('well_formed_role_swap', 'role', True)['effect'] = {'replace': ['file_type_bits'], 'preserve': ['permission_bits'], 'result': 'new_value'}
    altered('well_formed_wrong_limit', 'command', True)['conditions'][1]['value'] = 8192
    altered('well_formed_omitted_conditions', 'command', True)['conditions'] = []
    protocol = {'purpose': 'Contract input grammar and evidence identity controls, not semantic effectiveness.',
                'author': 'researcher development declarations, not provider-approved',
                'conditions_semantics': 'Conjunction; empty list declares unconditional domain. after constrains callback ordering, not a proof it occurs.',
                'unknowns': 'Configuration explicitly unknown remains unknown. Owner is declared, never inferred or verified.',
                'registry': 'Manually bound source identities, not compiler-resolved symbols; no automatic AST or revision provenance verification.',
                'scope': 'Two small contract kinds, not full Rust semantics or whole-crate requirements.',
                'negative_truth_controls': 'Well-formed false claims must pass grammar but remain behavior-unverified; do not present rejection statistics as truth accuracy.',
                'metrics': 'Expected grammar acceptance per case, two-pass equality, preservation of unverified behavior and unknown sharing.',
                'stop': 'Run all controls twice, no repairs based on outcomes; then evaluate semantic evidence linkage separately.'}
    for name, data in [('cases.json', cases), ('registry.json', registry), ('protocol.json', protocol)]:
        (folder / name).write_text(json.dumps(data, indent=2) + '\n')
    for source in [Path(__file__), root / 'scripts/check_crate_contract.py']:
        shutil.copy2(source, folder / source.name)
    frozen = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.iterdir())}
    (folder / 'frozen.json').write_text(json.dumps(frozen, indent=2) + '\n')
    passes = []
    for repeat in (1, 2):
        rows = []
        for case in cases:
            try:
                result = validate(case['contract'], registry, root)
                accepted = True
            except ValueError as error:
                result = {'error': str(error)}
                accepted = False
            rows.append({'id': case['id'], 'accepted': accepted, 'expected': case['accept'], 'result': result})
        passes.append(rows)
        (folder / f'result-{repeat}.json').write_text(json.dumps(rows, indent=2) + '\n')
    success = passes[0] == passes[1] and all(row['accepted'] == row['expected'] for row in passes[0])
    report = {'success': success, 'cases': len(cases), 'repeat_identical': passes[0] == passes[1],
              'accepted': sum(row['accepted'] for row in passes[0]), 'behavior_confirmed': 0,
              'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.iterdir())}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not success:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
