"""Freeze a next development batch before reading its candidate bodies."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (char.isalnum() or char in '-_') for char in args.run_id):
        raise ValueError('invalid ID')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/prospective-contract-sample-v1.json'
    plan = json.loads(protocol_path.read_text())
    candidates_path = ROOT / plan['population']
    detector = json.loads((candidates_path.parent / 'report.json').read_text())
    assert sha(candidates_path) == detector['artifacts_sha256']['candidates.json']
    corpus = ROOT / plan['corpus']
    corpus_report = json.loads((corpus / 'report.json').read_text())
    for name in ('units.json', 'units.zip', 'sources.zip'):
        assert sha(corpus / name) == corpus_report['artifacts_sha256'][name]
    assert sha(corpus / 'units.json') == detector['inputs'][str((corpus / 'units.json').relative_to(ROOT))]
    candidates = json.loads(candidates_path.read_text())
    by_file_id = {file_id: member for pair in candidates for file_id, member in zip(pair['file_ids'], pair['members'], strict=True)}
    excluded_paths = set()
    evidence_paths = [protocol_path, candidates_path, corpus / 'report.json']
    for relative in plan['exclusion_results']:
        path = ROOT / relative
        evidence_paths.append(path)
        for record in json.loads(path.read_text())['records']:
            for file_id in record['file_ids']:
                excluded_paths.add(by_file_id[file_id]['path'])
    for path in sorted(ROOT.glob(plan['exclude_seed_source_paths'])):
        evidence_paths.append(path)
        excluded_paths.update(member['path'] for member in json.loads(path.read_text())['members'])
    pilot = ROOT / plan['exclude_pilot_source_paths']
    evidence_paths.append(pilot)
    for case in json.loads(pilot.read_text())['cases']:
        excluded_paths.update(source['path'] for source in case['sources'])
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'selector.py')
    frozen = {'source_revision': corpus_report['revision'],
              'detector_revision': detector['source_revision'],
              'excluded_paths': sorted(excluded_paths),
              'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in evidence_paths},
              'selector_sha256': sha(Path(__file__))}
    (output / 'frozen.json').write_text(json.dumps(frozen, indent=2) + '\n')
    audit = []
    for pair in candidates:
        members = pair['members']
        reasons = []
        if any(member['test_path_hint'] for member in members):
            reasons.append('test_path_hint')
        if any(member['nested_in_function'] for member in members):
            reasons.append('nested_function')
        if any(member['path'] in excluded_paths for member in members):
            reasons.append('known_source_path')
        key = ':'.join(sorted(member['id'] for member in members))
        order = hashlib.sha256(('crate-contract-next-v1:' + key).encode()).hexdigest()
        audit.append({'key': key, 'order': order, 'file_ids': pair['file_ids'], 'paths': [member['path'] for member in members],
                      'reasons': reasons, 'selected': False})
    audit.sort(key=lambda row: row['order'])
    selected_paths = set()
    selected = []
    indexed = {tuple(pair['file_ids']): pair for pair in candidates}
    for row in audit:
        if row['reasons']:
            continue
        if selected_paths & set(row['paths']):
            row['reasons'].append('selected_file_overlap')
        elif len(selected) >= plan['budget']:
            row['reasons'].append('budget')
        else:
            row['selected'] = True
            selected.append(indexed[tuple(row['file_ids'])])
            selected_paths.update(row['paths'])
    (output / 'selection.json').write_text(json.dumps(selected, indent=2) + '\n')
    (output / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    with zipfile.ZipFile(corpus / 'units.zip') as units, zipfile.ZipFile(corpus / 'sources.zip') as sources:
        for index, pair in enumerate(selected, 1):
            for member_index, member in enumerate(pair['members'], 1):
                for suffix, content, expected in [('unit.rs', units.read(member['entry']), member['sha256']),
                                                  ('source.rs', sources.read(member['path']), member['source_sha256'])]:
                    assert hashlib.sha256(content).hexdigest() == expected
                    (output / f'pair-{index}-{member_index}-{suffix}').write_bytes(content)
    report = {'population_pairs': len(candidates), 'selected_pairs': len(selected), 'requested_pairs': plan['budget'],
              'eligibility_before_file_diversity': sum(not any(reason in ('test_path_hint', 'nested_function', 'known_source_path') for reason in row['reasons']) for row in audit),
              'shortfall': len(selected) < plan['budget'], 'blind_test': False,
              'artifact_sha256': {path.name: sha(path) for path in sorted(output.iterdir())}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))
    for index, pair in enumerate(selected, 1):
        print(index, [(member['path'], member['name']) for member in pair['members']])


if __name__ == '__main__':
    main()
