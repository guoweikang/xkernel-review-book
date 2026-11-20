"""Score fixed field predictions with explicit abstention, without model imports."""

import argparse
import json
from pathlib import Path

FIELDS = ('actor', 'action', 'object', 'polarity', 'force', 'condition')


def score(cases, predictions):
    expected = {row['id']: row for row in cases}
    actual = {row['id']: row for row in predictions}
    if len(expected) != len(cases) or len(actual) != len(predictions) or expected.keys() != actual.keys():
        raise ValueError('duplicate or mismatched IDs')
    counts = {field: {'total': 0, 'answered': 0, 'correct': 0, 'wrong': 0, 'abstained': 0} for field in FIELDS}
    families = {}
    for identity, case in expected.items():
        gold = case['gold']
        predicted = actual[identity]['fields']
        if set(gold) != set(FIELDS) or set(predicted) != set(FIELDS):
            raise ValueError('invalid field set')
        if any(not isinstance(value, str) or not value for value in gold.values()):
            raise ValueError('invalid reference value')
        if any(value is not None and (not isinstance(value, str) or not value) for value in predicted.values()):
            raise ValueError('invalid prediction value')
        family = families.setdefault(case['family'], {'records': 0, 'exact_records': 0})
        family['records'] += 1
        family['exact_records'] += predicted == gold
        for field in FIELDS:
            counter = counts[field]
            counter['total'] += 1
            value = predicted[field]
            if value is None:
                counter['abstained'] += 1
            else:
                counter['answered'] += 1
                counter['correct' if value == gold[field] else 'wrong'] += 1
    counts['pooled'] = {key: sum(counter[key] for counter in counts.values()) for key in ('total', 'answered', 'correct', 'wrong', 'abstained')}
    for counter in counts.values():
        counter['coverage'] = counter['answered'] / counter['total'] if counter['total'] else None
        counter['selective_exact'] = counter['correct'] / counter['answered'] if counter['answered'] else None
        counter['unconditional_exact'] = counter['correct'] / counter['total'] if counter['total'] else None
    return {'counts': counts, 'families': families, 'exact_records': sum(row['exact_records'] for row in families.values()), 'records': len(cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', type=Path)
    parser.add_argument('predictions', type=Path)
    args = parser.parse_args()
    print(json.dumps(score(json.loads(args.cases.read_text()), json.loads(args.predictions.read_text())), indent=2))


if __name__ == '__main__':
    main()
