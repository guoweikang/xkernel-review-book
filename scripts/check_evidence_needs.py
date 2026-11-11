"""Check coverage of reviewed identities, not semantic correctness of evidence needs."""

import argparse
from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / 'research/protocols/candidate-evidence-needs-v1.json'


def check(matrix):
    ledger = json.loads((ROOT / matrix['ledger']).read_text())
    expected = {family['family']: family for family in ledger['families']}
    rows = matrix['families']
    if len({row['family'] for row in rows}) != len(rows) or set(expected) != {row['family'] for row in rows}:
        raise ValueError('Family coverage differs')
    for row in rows:
        source = expected[row['family']]
        if row['pairs'] != source['pairs'] or row['current_validation'] != source['validation']:
            raise ValueError('Case identity or validation scope differs')
        if len(set(row['needs'])) != len(row['needs']) or not set(row['needs']).issubset(matrix['dimensions']):
            raise ValueError('Invalid evidence dimension')
        if not {'identity', 'reuse', 'benefit'}.issubset(row['needs']):
            raise ValueError('Missing common evidence needs')
        if not row['decision_gap'] or not row['evidence']:
            raise ValueError('Missing gap or supporting reference')
        for reference in row['evidence']:
            if not (ROOT / reference).is_file():
                raise ValueError('Missing reference')
    return {'families': len(rows), 'pairs': sum(len(row['pairs']) for row in rows),
            'need_counts_by_family': dict(Counter(need for row in rows for need in row['needs'])),
            'semantic_validation': 'not_performed', 'retrieval_evaluation': matrix['evaluation_status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text())
    result = check(matrix)
    if args.self_check:
        for mutation in ['missing_family', 'wrong_pair', 'unknown_dimension', 'wrong_validation']:
            changed = json.loads(json.dumps(matrix))
            if mutation == 'missing_family':
                changed['families'].pop()
            elif mutation == 'wrong_pair':
                changed['families'][0]['pairs'] = [[-1, -2]]
            elif mutation == 'unknown_dimension':
                changed['families'][0]['needs'].append('unknown')
            else:
                changed['families'][0]['current_validation'] = 'all_proven'
            try:
                check(changed)
            except ValueError:
                continue
            raise AssertionError('Invalid matrix accepted: ' + mutation)
        print('PASS: 18-pair matrix aligned; 4 negative controls rejected; no semantic accuracy claim')
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
