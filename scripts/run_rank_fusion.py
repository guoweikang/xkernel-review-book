import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil

import numpy as np
from scipy import sparse


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def order(values, reverse=False):
    indices = np.arange(len(values))
    return np.lexsort((-indices if reverse else indices, -values))


def ranks(values, reverse=False):
    result = np.empty(len(values), dtype=np.int64)
    result[order(values, reverse)] = np.arange(1, len(values) + 1)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/rank-fusion-v1.json'
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / 'research/evidence/runs' / protocol['parent']
    parent_report = json.loads((parent / 'report.json').read_text())
    for name, expected in parent_report['artifacts_sha256'].items():
        assert sha(parent / name) == expected, name
    inputs = ['eligible.json', 'score-matrices.npz', 'native-vectors.npz']
    for name in inputs:
        shutil.copyfile(parent / name, run / name)
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    queue_path = ROOT / 'research/evidence/runs/2026-11-16-common-budget-01/review-queue.json'
    shutil.copyfile(queue_path, run / 'development-queue.json')
    bindings_path = ROOT / 'research/evidence/runs/2026-11-09-source-doc-inventory-02/bindings.json'
    shutil.copyfile(bindings_path, run / 'bindings.json')
    dump(run / 'freeze.json', {'inputs': {name: sha(run / name) for name in inputs + ['development-queue.json', 'bindings.json', 'protocol.json', 'runner.py']}, 'parent_report_sha256': sha(parent / 'report.json'), 'python': platform.python_version(), 'numpy': np.__version__})
    eligible = json.loads((run / 'eligible.json').read_text())
    assert len(eligible) == 812 and eligible == sorted(eligible)
    matrix = np.load(run / 'score-matrices.npz')
    first, second = np.triu_indices(len(eligible), 1)
    assert len(first) == 329266
    code = np.array([round(float(value), 12) for value in matrix['code'][first, second]])
    document = np.array([round(float(value), 12) for value in matrix['document'][first, second]])
    code_rank, doc_rank = ranks(code), ranks(document)
    kappa = protocol['k']
    scores = {
        'code': code,
        'documentation': document,
        'mean': np.array([round(float(value), 12) for value in ((matrix['code'] + matrix['document']) / 2)[first, second]]),
        'rrf_complete': 1.0 / (kappa + code_rank) + 1.0 / (kappa + doc_rank),
        'rrf_positive': np.where(code > 0, 1.0 / (kappa + code_rank), 0) + np.where(document > 0, 1.0 / (kappa + doc_rank), 0),
        'rrf_complete_reverse_ties': 1.0 / (kappa + ranks(code, True)) + 1.0 / (kappa + ranks(document, True)),
    }
    nonzero = sparse.load_npz(run / 'native-vectors.npz').getnnz(axis=1) > 0
    bindings = {row['unit_id']: row['doc_text'] for row in json.loads((run / 'bindings.json').read_text())}
    text_present = np.array([bool(bindings[identity].strip()) for identity in eligible])
    queue = json.loads((run / 'development-queue.json').read_text())
    pair_index = {(eligible[left], eligible[right]): index for index, (left, right) in enumerate(zip(first, second))}
    report = {'eligible': len(eligible), 'pairs': len(first), 'nonzero_vector_units': int(nonzero.sum()), 'nonempty_text_units': int(text_present.sum()), 'methods': {}, 'overlaps': {}}
    top_sets = {}
    orders = {}
    for method, values in scores.items():
        indices = order(values)
        indices = indices[values[indices] > 0]
        orders[method] = indices
        top = indices[:protocol['budget']]
        top_sets[method] = set(map(int, top))
        cutoff = float(values[top[-1]])
        rank_lookup = {int(index): rank for rank, index in enumerate(indices, 1)}
        report['methods'][method] = {
            'positive_pairs': len(indices),
            'both_nonzero_vectors_top20': int(np.sum(nonzero[first[top]] & nonzero[second[top]])),
            'both_nonempty_text_top20': int(np.sum(text_present[first[top]] & text_present[second[top]])),
            'cutoff': cutoff,
            'above_cutoff': int(np.sum(values > cutoff)),
            'at_cutoff': int(np.sum(values == cutoff)),
            'development_anchor_ranks': {str(anchor): rank_lookup.get(pair_index[tuple(sorted(queue[anchor]['unit_ids']))]) for anchor in (7, 11, 27)},
        }
        rows = [[float(values[index]), eligible[first[index]], eligible[second[index]]] for index in indices[:100]]
        dump(run / f'{method}-top100.json', rows)
        if method in ('code', 'documentation', 'mean'):
            old_name = 'fusion' if method == 'mean' else method
            old = ROOT / 'research/evidence/runs/2026-11-16-common-budget-01' / f'{old_name}-top100.json'
            assert rows == json.loads(old.read_text()), method
    for method, chosen in top_sets.items():
        report['overlaps'][method] = {other: len(chosen & other_chosen) for other, other_chosen in top_sets.items()}
    np.savez_compressed(run / 'scores.npz', **scores)
    np.savez_compressed(run / 'orders.npz', **orders)
    report['artifacts_sha256'] = {path.name: sha(path) for path in sorted(run.iterdir()) if path.is_file()}
    dump(run / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifacts_sha256'}, indent=2))


if __name__ == '__main__':
    main()
