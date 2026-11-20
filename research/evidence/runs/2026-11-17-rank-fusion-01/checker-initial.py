import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def check(run):
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    protocol = json.loads((run / 'protocol.json').read_text())
    eligible = json.loads((run / 'eligible.json').read_text())
    pairs = list(itertools.combinations(range(len(eligible)), 2))
    matrix = np.load(run / 'score-matrices.npz')
    raw_code = [float(matrix['code'][left, right]) for left, right in pairs]
    raw_doc = [float(matrix['document'][left, right]) for left, right in pairs]
    code = [round(value, 12) for value in raw_code]
    document = [round(value, 12) for value in raw_doc]
    expected = {'code': code, 'documentation': document, 'mean': [round((left + right) / 2, 12) for left, right in zip(raw_code, raw_doc)]}
    for method in ('rrf_complete', 'rrf_positive', 'rrf_complete_reverse_ties'):
        accumulated = [0.0] * len(pairs)
        for values in (code, document):
            direction = -1 if method.endswith('reverse_ties') else 1
            ordered = sorted(range(len(pairs)), key=lambda index: (-values[index], direction * index))
            for rank, index in enumerate(ordered, 1):
                if method != 'rrf_positive' or values[index] > 0:
                    accumulated[index] += 1.0 / (protocol['k'] + rank)
        expected[method] = accumulated
    saved_scores = np.load(run / 'scores.npz')
    saved_orders = np.load(run / 'orders.npz')
    for method, values in expected.items():
        np.testing.assert_array_equal(saved_scores[method], values)
        ordered = sorted((index for index, value in enumerate(values) if value > 0), key=lambda index: (-values[index], index))
        assert saved_orders[method].tolist() == ordered
        rows = [[values[index], eligible[pairs[index][0]], eligible[pairs[index][1]]] for index in ordered[:100]]
        assert rows == json.loads((run / f'{method}-top100.json').read_text())
    assert all(expected['rrf_complete'][index] > expected['rrf_positive'][index] for index, value in enumerate(document) if value == 0)
    print(f'PASS: {len(pairs)} pairs, six complete score arrays and rank orders, zero-document contribution control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    arguments = parser.parse_args()
    check(ROOT / 'research/evidence/runs' / arguments.run)
