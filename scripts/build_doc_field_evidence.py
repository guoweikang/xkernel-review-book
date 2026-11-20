"""Bind development documentation fields to exact source excerpts."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(entry):
    source = (ROOT / entry['source']).read_bytes()
    if digest(source) != entry['source_sha256']:
        raise ValueError('source digest mismatch')
    if entry['provider_validated'] or entry['evaluation_eligible']:
        raise ValueError('source audit cannot promote validation status')
    if entry['state'] == 'unknown' and entry['evidence']:
        raise ValueError('unknown field has unsupported evidence upgrade')
    if entry['state'] != 'unknown' and not entry['evidence']:
        raise ValueError('missing field evidence')
    lines = source.decode().splitlines(keepends=True)
    for evidence in entry['evidence']:
        start, end = evidence['lines']
        if not 1 <= start <= end <= len(lines):
            raise ValueError('invalid source range')
        excerpt = ''.join(lines[start - 1:end])
        if evidence['excerpt'] != excerpt or evidence['sha256'] != digest(excerpt.encode()):
            raise ValueError('excerpt mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--repo', default='/root/codes/x-kernel')
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/doc-field-evidence-v1.json'
    protocol = json.loads(protocol_path.read_text())
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'builder.py')
    entries = []
    inputs = {}
    for packet_id, fields in protocol['ranges'].items():
        folder = ROOT / protocol['packet_run'] / packet_id
        packet_path = folder / 'packet.json'
        packet = json.loads(packet_path.read_text())
        inputs[str(packet_path.relative_to(ROOT))] = digest(packet_path.read_bytes())
        source_path = folder / 'source.txt'
        source = source_path.read_bytes()
        assert digest(source) == packet['source_sha256']
        lines = source.decode().splitlines(keepends=True)
        original = packet['arms']['D2_candidate']['fields']
        assert set(fields) == set(original)
        for name, ranges in fields.items():
            qualification = protocol['qualifications'].get(packet_id + '/' + name)
            entry = {'packet': packet_id, 'field': name, 'text': original[name]['text'],
                     'source_revision': packet['source_revision'], 'entity_identity': packet['entity_identity'],
                     'source': str(source_path.relative_to(ROOT)), 'source_sha256': digest(source),
                     'state': 'unknown' if not ranges else 'qualified' if qualification else 'source_linked',
                     'evidence_kind': 'design_statement_not_implementation_proof' if packet_id == 'firmware-ownership' else 'source_body_observation',
                     'qualification': qualification, 'provider_validated': False, 'evaluation_eligible': False,
                     'evidence': []}
            for start, end in ranges:
                excerpt = ''.join(lines[start - 1:end])
                entry['evidence'].append({'lines': [start, end], 'excerpt': excerpt, 'sha256': digest(excerpt.encode())})
            validate(entry)
            entries.append(entry)
    additional = protocol['additional_sources']
    for path in additional['paths']:
        data = subprocess.check_output(['git', '-C', args.repo, 'show', additional['revision'] + ':' + path])
        target = output / 'same-revision' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    rejected = []
    mutations = {
        'source_digest': lambda entry: entry.update(source_sha256='0' * 64),
        'provider_upgrade': lambda entry: entry.update(provider_validated=True),
        'evaluation_upgrade': lambda entry: entry.update(evaluation_eligible=True),
        'missing_evidence': lambda entry: entry.update(evidence=[]),
        'invalid_range': lambda entry: entry['evidence'][0].update(lines=[0, 1]),
        'changed_excerpt': lambda entry: entry['evidence'][0].update(excerpt='not the source'),
    }
    for name, mutation in mutations.items():
        entry = copy.deepcopy(entries[0])
        mutation(entry)
        try:
            validate(entry)
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    (output / 'fields.json').write_text(json.dumps(entries, indent=2) + '\n')
    (output / 'manifest.json').write_text(json.dumps({'packet_inputs': inputs, 'additional_revision': additional['revision']}, indent=2) + '\n')
    report = {'fields': len(entries), 'source_linked': sum(bool(entry['evidence']) for entry in entries),
              'qualified': sum(entry['state'] == 'qualified' for entry in entries),
              'unknown': sum(entry['state'] == 'unknown' for entry in entries),
              'rejected_controls': rejected, 'provider_validated': 0, 'detector_runs': 0,
              'artifact_sha256': {str(path.relative_to(output)): digest(path.read_bytes()) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
