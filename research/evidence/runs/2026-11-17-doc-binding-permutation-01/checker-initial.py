import argparse
import gzip
import hashlib
import json

import numpy as np
from scipy import sparse

from run_doc_tfidf import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    eligible = json.loads((run / 'eligible.json').read_text())
    indices = {identity: index for index, identity in enumerate(eligible)}
    permutations = json.loads((run / 'permutations.json').read_text())
    matrix = np.load(run / 'score-matrices.npz')
    vectors = sparse.load_npz(run / 'native-vectors.npz')
    native_doc = (vectors @ vectors.T).toarray()
    np.testing.assert_array_equal(native_doc, matrix['document'])
    nonzero = vectors.getnnz(axis=1) > 0
    assert np.count_nonzero(nonzero) == 200
    upper = np.triu_indices(len(eligible), 1)
    native_top = {}
    checked_rows = 0
    for arm in ('native', 'seed-17', 'seed-43', 'seed-91'):
        records = permutations[arm]['destination_to_source']
        assert [record['destination'] for record in records] == eligible
        mapping = [indices[record['source']] for record in records]
        assert sorted(mapping) == list(range(len(eligible)))
        for index, origin in enumerate(mapping):
            assert bool(nonzero[index]) == bool(nonzero[origin])
            if not nonzero[index] or arm == 'native':
                assert origin == index
            else:
                assert origin != index
        doc = native_doc[np.ix_(mapping, mapping)]
        np.testing.assert_array_equal(np.sort(doc[upper]), np.sort(native_doc[upper]))
        changed = sum((vectors[index] != vectors[origin]).nnz > 0 for index, origin in enumerate(mapping))
        assert changed == report['arms'][arm]['changed_document_vectors']
        for method, scores in [('documentation', doc), ('fusion', (matrix['code'] + doc) / 2)]:
            seen = set()
            first100 = []
            preceding = None
            scores_in_order = []
            with gzip.open(run / arm / f'{method}-ranking.tsv.gz', 'rt') as handle:
                for line in handle:
                    value, first, second = line.rstrip('\n').split('\t')
                    pair = (first, second)
                    assert first < second and pair not in seen
                    seen.add(pair)
                    score = float(value)
                    assert score > 0 and score == round(float(scores[indices[first], indices[second]]), 12)
                    key = (-score, first, second)
                    assert preceding is None or preceding <= key
                    preceding = key
                    if len(first100) < 100:
                        first100.append([score, first, second])
                    scores_in_order.append(score)
            detail = report['arms'][arm]['methods'][method]
            assert len(seen) == sum(round(float(score), 12) > 0 for score in scores[upper]) == detail['positive_pairs']
            assert first100 == json.loads((run / arm / f'{method}-top100.json').read_text())
            top = {tuple(row[1:]) for row in first100[:20]}
            if arm == 'native':
                native_top[method] = top
            assert len(top & native_top[method]) == detail['native_top20_intersection']
            assert sorted(top - native_top[method]) == detail['added_to_native_top20']
            assert sorted(native_top[method] - top) == detail['removed_from_native_top20']
            cutoff = first100[19][0]
            assert cutoff == detail['cutoff']
            assert sum(score == cutoff for score in scores_in_order) == detail['at_cutoff']
            assert sum(score > cutoff for score in scores_in_order) == detail['above_cutoff']
            checked_rows += len(seen)
    result = {'verified_ranked_rows': checked_rows, 'arms': 4, 'full_ranking_scores_order_uniqueness_coverage_verified': True, 'mapping_nonzero_and_empty_positions_verified': True, 'vector_recomputed_cosines_verified': True, 'limits': 'Checks implementation arithmetic and intervention, not semantic quality or external truth.'}
    (run / 'checked-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
