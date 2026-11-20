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
    with np.load(run / 'score-matrices.npz') as archive:
        matrix = {name: archive[name] for name in archive.files}
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
        info = report['methods'][method]
        cutoff = values[ordered[19]]
        assert info['positive_pairs'] == len(ordered)
        assert info['cutoff'] == cutoff
        assert info['above_cutoff'] == sum(value > cutoff for value in values)
        assert info['at_cutoff'] == sum(value == cutoff for value in values)
        bindings = {row['unit_id']: row['doc_text'] for row in json.loads((run / 'bindings.json').read_text())}
        coverage = sum(all(bindings[eligible[endpoint]].strip() for endpoint in pairs[index]) for index in ordered[:20])
        assert info['both_nonempty_text_top20'] == coverage
        nonzero_coverage = sum(all(matrix['document'][endpoint, endpoint] > 0 for endpoint in pairs[index]) for index in ordered[:20])
        assert info['both_nonzero_vectors_top20'] == nonzero_coverage
        queue = json.loads((run / 'development-queue.json').read_text())
        pair_lookup = {(eligible[left], eligible[right]): index for index, (left, right) in enumerate(pairs)}
        rank_lookup = {index: rank for rank, index in enumerate(ordered, 1)}
        assert info['development_anchor_ranks'] == {str(anchor): rank_lookup.get(pair_lookup[tuple(sorted(queue[anchor]['unit_ids']))]) for anchor in (7, 11, 27)}
        for other in expected:
            assert report['overlaps'][method][other] == len(set(ordered[:20]) & set(saved_orders[other][:20].tolist()))
    assert all(expected['rrf_complete'][index] > expected['rrf_positive'][index] for index, value in enumerate(document) if value == 0)
    print(f'PASS: {len(pairs)} pairs, six complete score arrays and rank orders, zero-document contribution control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    arguments = parser.parse_args()
    check(ROOT / 'research/evidence/runs' / arguments.run)
