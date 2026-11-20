"""Independently check stored binary TF-IDF cosine scores and repeat identity."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--repeat', required=True, type=Path)
    args = parser.parse_args()
    for relative, expected in json.loads((args.run / 'freeze.json').read_text()).items():
        path = Path(relative)
        if not path.is_absolute():
            path = ROOT / path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
    report = json.loads((args.run / 'report.json').read_text())
    features = json.loads((args.run / 'features.json').read_text())
    assert len(features) == 812
    comparisons = 0
    for method in ('call_set', 'call_order'):
        counts = Counter(token for value in features.values() for token in set(value[method]))
        vectors = {}
        for unit, value in features.items():
            weights = {token: math.log(813 / (1 + counts[token])) + 1 for token in set(value[method])}
            norm = math.sqrt(sum(weight * weight for weight in weights.values()))
            vectors[unit] = {token: weight / norm for token, weight in weights.items()}
        assert sum(bool(vector) for vector in vectors.values()) == report['methods'][method]['nonzero_units']
        rows = json.loads((args.run / (method + '-top100.json')).read_text())
        assert rows == sorted(rows, key=lambda row: (-row[0], row[1], row[2]))
        for score, first, second in rows:
            assert first < second
            independent = sum(value * vectors[second].get(token, 0)
                              for token, value in vectors[first].items())
            assert abs(independent - score) <= 1e-11, (method, first, second)
            comparisons += 1
        for suffix in ('-top100.json', '-diagnostics.json'):
            assert (args.run / (method + suffix)).read_bytes() == (args.repeat / (method + suffix)).read_bytes()
    for name in ('features.json', 'review-queue.json', 'report.json', 'freeze.json', 'protocol.json', 'runner.py'):
        assert (args.run / name).read_bytes() == (args.repeat / name).read_bytes(), name
    selection = json.loads((args.run / 'review-queue.json').read_text())
    assert len(selection) <= 6 and len({tuple(row['pair']) for row in selection}) == len(selection)
    print(json.dumps({'independent_cosine_checks': comparisons, 'repeated_artifacts_equal': True,
                      'selected_pairs': len(selection), 'semantic_relevance_validated': False}, indent=2))


if __name__ == '__main__':
    main()
