"""Check frozen field scores, abstention controls and archived parse integrity."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from score_contract_fields import FIELDS, score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    folder = parser.parse_args().folder
    report = json.loads((folder / 'report.json').read_text())
    for name, digest in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    cases = json.loads((folder / 'cases.json').read_text())
    predictions = json.loads((folder / 'predictions-1.json').read_text())
    scores = json.loads((folder / 'scores.json').read_text())
    assert score(cases, predictions) == scores
    correct = answered = 0
    by_id = {row['id']: row['fields'] for row in predictions}
    for case in cases:
        for field, expected in case['gold'].items():
            observed = by_id[case['id']][field]
            answered += observed is not None
            correct += observed == expected
    assert scores['counts']['pooled']['correct'] == correct
    assert scores['counts']['pooled']['answered'] == answered
    for name in ('predictions', 'parses'):
        assert (folder / f'{name}-1.json').read_bytes() == (folder / f'{name}-2.json').read_bytes()
    texts = {row['id']: row['text'] for row in cases}
    parses = json.loads((folder / 'parses-1.json').read_text())
    assert len(parses) == len(cases) and {row['id'] for row in parses} == texts.keys()
    for record in parses:
        tokens = record['tokens']
        for position, token in enumerate(tokens):
            assert token['id'] == position
            assert texts[record['id']][token['start']:token['end']] == token['text']
            seen = set()
            while True:
                assert position not in seen
                seen.add(position)
                head = tokens[position]['head']
                assert 0 <= head < len(tokens)
                if head == position:
                    assert tokens[position]['dep'] == 'ROOT'
                    break
                position = head
    identity = [{'id': row['id'], 'fields': dict(row['gold'])} for row in cases]
    assert score(cases, identity)['counts']['pooled']['unconditional_exact'] == 1
    empty = [{'id': row['id'], 'fields': dict.fromkeys(FIELDS)} for row in cases]
    empty_score = score(cases, empty)['counts']['pooled']
    assert empty_score['coverage'] == 0 and empty_score['selective_exact'] is None
    wrong = copy.deepcopy(identity)
    wrong[0]['fields']['actor'] = 'deliberately-wrong'
    assert score(cases, wrong)['counts']['pooled']['wrong'] == 1
    bad_field = copy.deepcopy(identity)
    del bad_field[0]['fields']['actor']
    bad_type = copy.deepcopy(identity)
    bad_type[0]['fields']['actor'] = 123
    rejected = 0
    for invalid in (identity[:-1], identity + [identity[0]], bad_field, bad_type):
        try:
            score(cases, invalid)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('invalid predictions accepted')
    print(json.dumps({'artifact_integrity': True, 'repeat_identical': True,
                      'score_controls': 3, 'invalid_controls_rejected': rejected,
                      'independent_reference_labels': False}))


if __name__ == '__main__':
    main()
