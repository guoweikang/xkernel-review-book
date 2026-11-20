"""Package scoped research claims without promoting them to relevance labels."""

import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(record):
    if record['split'] != 'development' or record['relation_label'] != 'unknown':
        raise ValueError('development observations cannot become test labels')
    if record['optimization_benefit'] != 'unverified' or record['independent_adjudication'] != 'not_available':
        raise ValueError('no benefit or independent adjudication evidence')
    card_path = ROOT / record['card']
    if sha(card_path) != record['card_sha256']:
        raise ValueError('seed identity mismatch')
    card = json.loads(card_path.read_text())
    if card['id'] != record['id'] or card['revision'] != record['revision']:
        raise ValueError('source identity mismatch')
    for member in card['members']:
        if sha(card_path.parent / member['unit_file']) != member['sha256']:
            raise ValueError('unit hash mismatch')
        if sha(card_path.parent / member['source_file']) != member['source_sha256']:
            raise ValueError('source hash mismatch')
    if len(record['claims']) != 2:
        raise ValueError('expected observation and open proposition')
    for claim in record['claims']:
        if claim['state'] not in ('supported', 'refuted', 'unknown'):
            raise ValueError('invalid claim state')
        if not claim['scope'] or not claim['statement'] or not claim['needed']:
            raise ValueError('scope and remaining evidence are required')
        if claim['state'] != 'unknown' and not claim['evidence']:
            raise ValueError('a conclusion needs evidence')
        if claim['basis'] == 'not_evaluated' and claim['state'] != 'unknown':
            raise ValueError('unevaluated claim cannot be resolved')
        for evidence in claim['evidence']:
            if sha(ROOT / evidence['path']) != evidence['sha256']:
                raise ValueError('evidence mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    protocol_path = ROOT / 'research/protocols/confirmation-claims-v1.json'
    protocol = json.loads(protocol_path.read_text())
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'builder.py')
    records = []
    for case in protocol['cases']:
        card_path = ROOT / protocol['seed_run'] / case['id'] / 'card.json'
        card = json.loads(card_path.read_text())
        paths = [str(card_path.relative_to(ROOT))] + case['evidence']
        evidence = [{'path': path, 'sha256': sha(ROOT / path)} for path in paths]
        record = {key: card[key] for key in ('id', 'revision', 'family', 'origin_group', 'split',
                                             'relation_label', 'optimization_benefit', 'independent_adjudication')}
        record.update(card=str(card_path.relative_to(ROOT)), card_sha256=sha(card_path), claims=[
            {'statement': case['claim'], 'dimension': case['dimension'], 'state': case['state'],
             'basis': case['basis'], 'scope': case['scope'], 'evidence': evidence, 'needed': case['needed']},
            {'statement': case['open_claim'], 'dimension': 'sharing_or_replacement', 'state': 'unknown',
             'basis': 'not_evaluated', 'scope': case['scope'], 'evidence': [], 'needed': case['needed']}
        ])
        validate(record)
        records.append(record)
    rejected = []
    mutations = {
        'test_promotion': lambda record: record.update(split='test'),
        'relevance_promotion': lambda record: record.update(relation_label='positive'),
        'benefit_promotion': lambda record: record.update(optimization_benefit='verified'),
        'adjudication_promotion': lambda record: record.update(independent_adjudication='complete'),
        'missing_scope': lambda record: record['claims'][0].update(scope=''),
        'missing_evidence': lambda record: record['claims'][0].update(evidence=[]),
        'evidence_tamper': lambda record: record['claims'][0]['evidence'][0].update(sha256='0' * 64),
        'unsupported_conclusion': lambda record: record['claims'][1].update(state='supported'),
    }
    for name, mutate in mutations.items():
        record = copy.deepcopy(records[0])
        mutate(record)
        try:
            validate(record)
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    (output / 'claims.json').write_text(json.dumps(records, indent=2) + '\n')
    report = {'scope': protocol['purpose'], 'cases': len(records), 'claims': 2 * len(records),
              'states': dict(Counter(claim['state'] for record in records for claim in record['claims'])),
              'rejected_controls': rejected, 'independent_labels': 0,
              'warning': 'Checks validate evidence integrity and schema, not the semantic correctness of judgments',
              'sha256': {path.name: sha(path) for path in output.iterdir() if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
