"""Validate seed packaging and guard development evidence against label inflation."""

from copy import deepcopy
import json
from pathlib import Path
import sys

from package_rust_development_seeds import ROOT, RUNS, digest, load


def validate(card, files):
    if card['split'] != 'development' or card['relation_label'] != 'unknown' or card['optimization_benefit'] != 'unverified':
        raise ValueError('Development seed promoted to test or truth')
    if card['independent_adjudication'] != 'not_available':
        raise ValueError('No independent adjudication in this pack')
    if not card['configuration_scope'] or not card['challenge']['status']:
        raise ValueError('Configuration and challenge status required')
    if len({member['id'] for member in card['members']}) != len(card['members']):
        raise ValueError('Duplicate source member')
    for member in card['members']:
        source, snippet = files[member['source_file']], files[member['unit_file']]
        if digest(source) != member['source_sha256'] or digest(snippet) != member['sha256']:
            raise ValueError('Source content changed')
        start, end = member['range']
        if not 0 <= start < end <= len(source) or source[start:end] != snippet:
            raise ValueError('Invalid source range')
        if source[:start].count(b'\n') + 1 != member['start_line'] or source[:end].count(b'\n') + 1 != member['end_line']:
            raise ValueError('Line/range mismatch')
        if member['cfg'] != 'not_evaluated':
            raise ValueError('Source inventory is not compiled configuration membership')


def main():
    root = RUNS / sys.argv[1]
    report = load(root / 'report.json')
    for name, checksum in report['artifact_sha256'].items():
        assert digest((root / name).read_bytes()) == checksum
    selection = load(root / 'selection.json')
    assert len(report['seed_cards']) == len(selection['seeds']) == 6
    by_id = {seed['id']: seed for seed in selection['seeds']}
    cards = []
    for entry in report['seed_cards']:
        card = load(root / entry['card'])
        assert card['revision'] == selection['revision']
        for key, value in by_id[entry['id']].items():
            assert card[key] == value
        files = {path.name: path.read_bytes() for path in (root / entry['id']).glob('*.rs')}
        validate(card, files)
        for name, checksum in card['evidence_sha256'].items():
            assert digest((ROOT / name).read_bytes()) == checksum
        cards.append((card, files))
    mutations = {
        'test_promotion': lambda card: card.update(split='test'),
        'truth_promotion': lambda card: card.update(relation_label='positive'),
        'benefit_promotion': lambda card: card.update(optimization_benefit='proven'),
        'review_promotion': lambda card: card.update(independent_adjudication='approved'),
        'missing_config': lambda card: card.update(configuration_scope=''),
        'duplicate_member': lambda card: card['members'].append(card['members'][0]),
        'wrong_range': lambda card: card['members'][0]['range'].__setitem__(0, 0),
        'compiled_membership': lambda card: card['members'][0].update(cfg='compiled')
    }
    passed = []
    for name, mutate in mutations.items():
        card, files = deepcopy(cards[0])
        mutate(card)
        try:
            validate(card, files)
        except ValueError:
            passed.append(name)
        else:
            raise AssertionError(name)
    card, files = deepcopy(cards[0])
    files[card['members'][0]['source_file']] += b'\n'
    try:
        validate(card, files)
    except ValueError:
        passed.append('tampered_source')
    else:
        raise AssertionError('tampered_source')
    result = {'cards': len(cards), 'source_members': sum(len(card['members']) for card, files in cards),
              'negative_controls': passed, 'scope': 'source/provenance integrity only, not relation correctness',
              'checker_sha256': digest(Path(__file__).read_bytes())}
    (root / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
