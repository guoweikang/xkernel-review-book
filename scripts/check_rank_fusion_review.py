import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--repeat', required=True)
    args = parser.parse_args()
    runs = ROOT / 'research/evidence/runs'
    run = runs / args.run
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    protocol = json.loads((run / 'protocol.json').read_text())
    parent = runs / protocol['parent']
    repeated = runs / args.repeat
    original_report = json.loads((parent / 'report.json').read_text())
    repeat_report = json.loads((repeated / 'report.json').read_text())
    assert original_report == repeat_report
    for name, expected in original_report['artifacts_sha256'].items():
        assert hashlib.sha256((repeated / name).read_bytes()).hexdigest() == expected, name
    with np.load(parent / 'scores.npz') as archive:
        scores = {name: archive[name] for name in archive.files}
    with np.load(parent / 'orders.npz') as archive:
        orders = {name: archive[name] for name in archive.files}
    identities = json.loads((parent / 'eligible.json').read_text())
    pairs = list(itertools.combinations(identities, 2))
    selected = sorted({int(index) for order in orders.values() for index in order[:20]})
    cases = json.loads((run / 'reviewer/cases.json').read_text())
    analyst = json.loads((run / 'analyst-only.json').read_text())
    bindings = {row['unit_id']: row['doc_text'] for row in json.loads((parent / 'bindings.json').read_text())}
    assert len(cases) == len(analyst) == len(selected) == report['cases_prepared']
    assert report['cases_reviewed'] == 0
    complete_ranks = {}
    for method in ('code', 'documentation'):
        complete_ranks[method] = {index: rank for rank, index in enumerate(sorted(range(len(pairs)), key=lambda index: (-scores[method][index], index)), 1)}
    for case, detail, index in zip(cases, analyst, selected):
        assert case['case_id'] == detail['case_id']
        assert tuple(detail['unit_ids']) == pairs[index]
        assert all(value is None for value in case['assessment'].values())
        for side, member in zip(('left', 'right'), case['members']):
            folder = run / 'reviewer' / case['case_id']
            assert hashlib.sha256((folder / f'{side}-snippet.rs').read_bytes()).hexdigest() == member['sha256']
            assert hashlib.sha256((folder / f'{side}-source.rs').read_bytes()).hexdigest() == member['source_sha256']
            assert (folder / f'{side}-doc.txt').read_text() == bindings[member['id']]
        for method, component in detail['component'].items():
            assert component['complete_rank'] == complete_ranks[method][index]
            assert component['score'] == scores[method][index]
            assert component['tie_group_size'] == int(np.sum(scores[method] == scores[method][index]))
            assert component['complete_contribution'] == 1 / (60 + complete_ranks[method][index])
        for method in ('rrf_complete', 'rrf_positive'):
            key = 'complete_contribution' if method == 'rrf_complete' else 'positive_contribution'
            assert sum(component[key] for component in detail['component'].values()) == scores[method][index]
    zero_count = int(np.count_nonzero(scores['documentation'] == 0))
    assert zero_count == report['pair_categories']['absent_text'] + report['pair_categories']['present_zero']
    assert report['complete_zero_doc_upper_bound'] == 1 / 61 + 1 / (61 + len(pairs) - zero_count)
    assert report['complete_zero_doc_upper_bound'] < min(original_report['methods'][method]['cutoff'] for method in ('rrf_complete', 'rrf_positive', 'rrf_complete_reverse_ties'))
    print(f'PASS: repeat artifacts identical; {len(cases)} unreviewed cases cover exact union; source hashes, component ranks/contributions and exclusion bound checked')


if __name__ == '__main__':
    main()
