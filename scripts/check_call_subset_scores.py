"""Recompute both subset score columns without the ranking implementation."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

from prepare_rust_token_bags import decode_bag


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--repeat', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    frozen = read(args.run / 'freeze.json')
    inputs = {}
    for name, entry in frozen['inputs'].items():
        path = ROOT / entry['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], name
        inputs[name] = path
    identities = read(args.run / 'eligible.json')
    assert identities == sorted(set(identities)) and len(identities) == 429
    features = {row['unit_id']: set(row['call_set']) for row in read(args.run / 'features.json')}
    assert set(features) == set(identities)
    frequencies = Counter(feature for values in features.values() for feature in values)
    vectors = {}
    for identity, values in features.items():
        weights = {feature: 1 + math.log((1 + len(identities)) / (1 + frequencies[feature]))
                   for feature in values}
        norm = math.sqrt(sum(value * value for value in weights.values()))
        vectors[identity] = {feature: value / norm for feature, value in weights.items()}
    tokens = read(inputs['tokens'])
    token_rows = tokens['records']
    token_by_id = {row['unit_id']: row for row in token_rows}
    bags_by_file = {int(line.split(',')[1]): decode_bag(line)
                    for line in inputs['bags'].read_text().splitlines()}
    bags = {identity: bags_by_file[token_by_id[identity]['file_id']] for identity in identities}
    counts = {identity: sum(bag.values()) for identity, bag in bags.items()}
    actual = np.load(args.run / 'pair-scores.npy', allow_pickle=False)
    assert actual.shape == (91806, 2)
    rankings = {'code': [], 'call_set': []}
    largest_error = 0.0
    for index, (first, second) in enumerate(itertools.combinations(identities, 2)):
        shared = sum(min(count, bags[second].get(token, 0)) for token, count in bags[first].items())
        code = shared / max(counts[first], counts[second])
        cosine = sum(value * vectors[second].get(feature, 0)
                     for feature, value in vectors[first].items())
        for column, (method, expected) in enumerate((('code', code), ('call_set', cosine))):
            error = abs(float(actual[index, column]) - expected)
            largest_error = max(largest_error, error)
            assert error < 1e-11, (index, method, error)
            rounded = round(expected, 12)
            if rounded > 0:
                rankings[method].append([rounded, first, second])
    for method, rows in rankings.items():
        rows.sort(key=lambda row: (-row[0], row[1], row[2]))
        assert rows[:100] == read(args.run / (method + '-top100.json')), method
        assert rows[:20] == read(args.run / (method + '-top20.json')), method
    for filename in ('pair-scores.npy', 'features.json', 'eligible.json', 'review-queue.json',
                     'selection-ledger.json', 'report.json', 'freeze.json', 'runner.py', 'protocol.json'):
        assert (args.run / filename).read_bytes() == (args.repeat / filename).read_bytes(), filename
    result = {'independently_recomputed_pairs': len(actual), 'score_comparisons': 2 * len(actual),
              'max_absolute_error': largest_error, 'top20_and_top100_reconstructed': True,
              'repeat_artifacts_equal': True, 'semantic_effectiveness_measured': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
