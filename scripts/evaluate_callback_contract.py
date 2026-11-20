"""Evaluate a bounded callback contract against archived model event traces."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

from check_crate_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_obligation(contract, registry):
    validate(contract, registry, ROOT)
    if contract['kind'] != 'callback' or contract['effect']['target'] != 'self.write':
        raise ValueError('unmapped callback')
    effect = contract['effect']
    if (effect['payload'], effect['after'], effect['on_collection_failure']) != ('whole', 'whole_collection', 'no_callback'):
        raise ValueError('unsupported callback semantics')
    for condition in contract['conditions']:
        if condition['subject'] != 'input_length' or condition['operator'] not in ('gt', 'le') or type(condition['value']) is not int:
            raise ValueError('unmapped condition')
    return {'conditions': contract['conditions'], 'count': effect['count']}


def evaluate(obligation, row, length):
    for condition in obligation['conditions']:
        inside = length > condition['value'] if condition['operator'] == 'gt' else length <= condition['value']
        if not inside:
            return {'status': 'outside_declared_domain', 'checks': {}}
    copied = 0
    callback_positions = []
    collection_failed = False
    for event in row['trace']:
        if event.startswith('copy:'):
            value = event.split(':')[1]
            if value.isdecimal():
                copied += int(value)
                collection_failed |= int(value) == 0
            elif value == 'BadAddress':
                collection_failed = True
            else:
                raise ValueError('unmapped copy event')
        elif event.startswith('callback:'):
            callback_positions.append(copied)
        elif not event.startswith('rewind:'):
            raise ValueError('unmapped event')
    if len(callback_positions) != len(row['calls']):
        raise ValueError('callback log mismatch')
    checks = {'whole_payload': all(call['payload'] == [index % 251 for index in range(length)] for call in row['calls']),
              'after_whole_collection': all(position == length for position in callback_positions),
              'no_callback_on_collection_failure': not collection_failed or not row['calls']}
    if not collection_failed and copied == length:
        checks['callback_count'] = len(row['calls']) == obligation['count']
    elif not collection_failed:
        return {'status': 'insufficient_trace', 'checks': checks}
    return {'status': 'observed_satisfied' if all(checks.values()) else 'counterexample',
            'checks': checks, 'copied': copied, 'collection_failed': collection_failed,
            'callbacks': len(row['calls'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    parent = ROOT / 'research/evidence/runs/2026-11-16-crate-contract-01'
    archived = ROOT / 'research/evidence/runs/2026-11-12-stream-command-01'
    for source in (parent, archived):
        report = json.loads((source / 'report.json').read_text())
        for name, expected in report['artifact_sha256'].items():
            if sha(source / name) != expected:
                raise ValueError('changed archived artifact')
    cases = json.loads((parent / 'cases.json').read_text())
    contract = next(case['contract'] for case in cases if case['id'] == 'command')
    registry = json.loads((parent / 'registry.json').read_text())
    changed = copy.deepcopy(contract)
    changed['effect']['count'] = 2
    declarations = {'once': contract, 'twice': changed}
    lengths = {'complete': 4, 'empty': 0, 'oversize': 4097, 'short_success': 4, 'short_then_fault': 4, 'callback_fault': 4}
    protocol = {'design': 'Replay 4 archived mode/repeat trace files x 12 rows x 2 declarations = 96 evaluations; no new Rust execution.',
                'input_lengths': lengths, 'payload_model': 'byte[index] = index % 251, from frozen original harness',
                'bindings': 'manual callback event mapping to self.write; command owns declaration, scalar is evaluated as a replacement candidate, not falsely rebound as the same source entity',
                'semantics': 'Count applies after successful collection, including callback failure. Collection failure requires no callback. Out-of-domain is neither pass nor failure.',
                'expected_per_trace_file': {'once': {'observed_satisfied': 6, 'counterexample': 2, 'outside_declared_domain': 4},
                                            'twice': {'observed_satisfied': 1, 'counterexample': 7, 'outside_declared_domain': 4}},
                'limits': 'Previously seen development traces with modeled dependencies; valid rewind, no cursor effects on failed copy, no short callback returns. No zero-copy scenario or incomplete-trace scenario exercised.',
                'stop': 'All archived conditions retained; no tuning and no performance/novelty or general sharing claim.'}
    for name, value in [('declarations.json', declarations), ('registry.json', registry), ('protocol.json', protocol)]:
        (folder / name).write_text(json.dumps(value, indent=2) + '\n')
    for source in (Path(__file__), ROOT / 'scripts/check_crate_contract.py'):
        shutil.copy2(source, folder / source.name)
    files = [f'{mode}-{repeat}-execute.stdout' for mode in ('debug', 'release') for repeat in (1, 2)]
    for name in files:
        shutil.copy2(archived / name, folder / name)
    (folder / 'source-manifest.json').write_text(json.dumps({'trace_run': str(archived.relative_to(ROOT)),
        'trace_report_sha256': sha(archived / 'report.json'), 'contract_report_sha256': sha(parent / 'report.json')}, indent=2) + '\n')
    (folder / 'frozen.json').write_text(json.dumps({path.name: sha(path) for path in sorted(folder.iterdir())}, indent=2) + '\n')
    results = []
    for name in files:
        traces = [json.loads(line) for line in (folder / name).read_text().splitlines()]
        assert len(traces) == 12 and len({(row['scenario'], row['adapter']) for row in traces}) == 12
        for identity, declaration in declarations.items():
            obligation = compile_obligation(declaration, registry)
            for row in traces:
                results.append({'file': name, 'declaration': identity, 'scenario': row['scenario'], 'adapter': row['adapter'],
                                **evaluate(obligation, row, lengths[row['scenario']])})
    (folder / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    groups = {}
    for name in files:
        groups[name] = {}
        for declaration in declarations:
            selected = [row for row in results if row['file'] == name and row['declaration'] == declaration]
            counts = {state: sum(row['status'] == state for row in selected) for state in ('observed_satisfied', 'counterexample', 'outside_declared_domain')}
            assert counts == protocol['expected_per_trace_file'][declaration], counts
            groups[name][declaration] = counts
    report = {'evaluations': len(results), 'groups': groups, 'new_rust_executions': 0, 'sharing': 'unknown',
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir())}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'evaluations': len(results), 'per_file': groups[files[0]], 'new_rust_executions': 0}, indent=2))


if __name__ == '__main__':
    main()
