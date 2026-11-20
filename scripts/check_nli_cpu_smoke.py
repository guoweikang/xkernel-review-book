"""Recompute labels and counts from saved logits without loading the model."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    folder = ROOT / 'research/evidence/runs' / args.run_id
    report = json.loads((folder / 'report.json').read_text())
    for filename, digest in report['artifact_sha256'].items():
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != digest:
            raise ValueError('artifact mismatch')
    plan = json.loads((folder / 'protocol.json').read_text())
    with (ROOT / plan['data']).open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    groups = defaultdict(list)
    for row in rows:
        groups[row['subcase']].append(row)
    selected = [row for group in sorted(groups) for row in sorted(groups[group], key=lambda row: row['pairID'])[:10]]
    identities = [row['pairID'] for row in selected]
    if identities != json.loads((folder / 'selected-ids.json').read_text()):
        raise ValueError('sample selection differs')
    passes = []
    for repeat in (1, 2):
        predictions = [json.loads(line) for line in (folder / f'predictions-{repeat}.jsonl').read_text().splitlines()]
        if [row['pairID'] for row in predictions] != identities:
            raise ValueError('prediction coverage differs')
        counts = defaultdict(lambda: [0, 0])
        for source, prediction in zip(selected, predictions):
            scores = prediction['logits']
            if len(scores) != 3 or not all(math.isfinite(value) for value in scores):
                raise ValueError('invalid logits')
            label = ['contradiction', 'entailment', 'neutral'][scores.index(max(scores))]
            binary = 'entailment' if label == 'entailment' else 'non-entailment'
            if prediction['label'] != label or prediction['binary_label'] != binary:
                raise ValueError('label decoding differs')
            for group in ['overall', 'gold:' + source['gold_label'], 'subcase:' + source['subcase']]:
                counts[group][0] += int(binary == source['gold_label'])
                counts[group][1] += 1
        if repeat == 1 and {key: {'correct': hits, 'total': total, 'accuracy': hits / total} for key, (hits, total) in counts.items()} != report['metrics']:
            raise ValueError('metric mismatch')
        passes.append(predictions)
    difference = max(abs(left - right) for first, second in zip(*passes) for left, right in zip(first['logits'], second['logits']))
    agreement = sum(first['label'] == second['label'] for first, second in zip(*passes)) / len(selected)
    if difference != report['max_logit_difference'] or agreement != report['prediction_agreement']:
        raise ValueError('repeat statistic mismatch')
    print('PASS: selection, 600 saved predictions, decoding, grouped metrics, repeat statistics and hashes')


if __name__ == '__main__':
    main()
