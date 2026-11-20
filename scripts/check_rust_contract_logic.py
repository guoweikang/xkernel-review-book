"""Check hand-derived control labels, saved logits and artifact integrity."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'condition/preserved': 'entailment', 'condition/converse': 'neutral',
    'condition/unconditional': 'neutral', 'condition/contrapositive': 'entailment',
    'field_role/changed': 'entailment', 'field_role/preserved': 'entailment',
    'field_role/swapped': 'contradiction', 'field_role/denied': 'contradiction',
    'document_report/report_preserved': 'entailment', 'document_report/actual_promoted': 'neutral',
    'document_report/actual_denied': 'neutral', 'document_report/report_denied': 'contradiction',
    'norm_vs_actual/norm_preserved': 'entailment', 'norm_vs_actual/actual_promoted': 'neutral',
    'norm_vs_actual/actual_denied': 'neutral', 'norm_vs_actual/norm_denied': 'contradiction',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    folder = ROOT / 'research/evidence/runs' / args.run_id
    report = json.loads((folder / 'report.json').read_text())
    for filename, digest in report['artifact_sha256'].items():
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != digest:
            raise ValueError('artifact hash differs')
    references = json.loads((folder / 'reference.json').read_text())
    if len(references) != 16 or {row['id']: row['label'] for row in references} != EXPECTED:
        raise ValueError('reference disagrees with hand-derived truth table')
    counts = defaultdict(lambda: {'total': 0, 'three_way_correct': 0, 'binary_correct': 0})
    passes = []
    for repeat in (1, 2):
        rows = json.loads((folder / f'predictions-{repeat}.json').read_text())
        if [row['id'] for row in rows] != [row['id'] for row in references]:
            raise ValueError('coverage mismatch')
        for row in rows:
            scores = row['logits']
            if len(scores) != 3 or not all(math.isfinite(value) for value in scores):
                raise ValueError('invalid logits')
            expected = ['contradiction', 'entailment', 'neutral'][scores.index(max(scores))]
            if expected != row['label']:
                raise ValueError('decoded label mismatch')
            if repeat == 1:
                for group in ('overall', row['id'].split('/')[0]):
                    counts[group]['total'] += 1
                    counts[group]['three_way_correct'] += int(expected == EXPECTED[row['id']])
                    counts[group]['binary_correct'] += int((expected == 'entailment') == (EXPECTED[row['id']] == 'entailment'))
        passes.append(rows)
    if dict(counts) != report['metrics'] or (passes[0] == passes[1]) != report['predictions_equal']:
        raise ValueError('metrics differ')
    print('PASS: 16 hand-derived labels, 32 logits, grouped metrics, repeats and hashes; English alignment remains an assumption')


if __name__ == '__main__':
    main()
