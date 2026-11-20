import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/rank-fusion-review-v1.json'
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / 'research/evidence/runs' / protocol['parent']
    report = json.loads((parent / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert sha(parent / name) == expected, name
    authority = ROOT / 'research/evidence/runs/2026-11-17-doc-binding-permutation-01/inputs.json'
    original_inputs = json.loads(authority.read_text())['inputs']
    corpus = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
    assert sha(corpus / 'units.json') == original_inputs['units']['sha256']
    assert sha(parent / 'bindings.json') == original_inputs['docs']['sha256']
    units = {row['id']: row for row in json.loads((corpus / 'units.json').read_text())}
    bindings = {row['unit_id']: row['doc_text'] for row in json.loads((parent / 'bindings.json').read_text())}
    eligible = json.loads((parent / 'eligible.json').read_text())
    pairs = list(itertools.combinations(eligible, 2))
    with np.load(parent / 'scores.npz') as archive:
        scores = {name: archive[name] for name in archive.files}
    with np.load(parent / 'orders.npz') as archive:
        orders = {name: archive[name] for name in archive.files}
    selected = sorted(set(int(index) for method in orders for index in orders[method][:20]))
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    dump(run / 'freeze.json', {'parent_report': sha(parent / 'report.json'), 'protocol': sha(protocol_path), 'runner': sha(Path(__file__)), 'source_inputs': {name: sha(corpus / name) for name in ('units.json', 'units.zip', 'sources.zip')}, 'authority': sha(authority)})
    reviewer = run / 'reviewer'
    reviewer.mkdir()
    rank_maps = {method: {int(index): rank for rank, index in enumerate(orders[method], 1)} for method in orders}
    tie_counts = {method: Counter(scores[method].tolist()) for method in ('code', 'documentation')}
    documents_positive = int(np.count_nonzero(scores['documentation'] > 0))
    categories = Counter()
    for index, (left, right) in enumerate(pairs):
        category = 'absent_text' if not bindings[left].strip() or not bindings[right].strip() else ('present_zero' if scores['documentation'][index] == 0 else 'present_positive')
        categories[category] += 1
    cases, analyst = [], []
    with zipfile.ZipFile(corpus / 'units.zip') as snippets, zipfile.ZipFile(corpus / 'sources.zip') as sources:
        for serial, index in enumerate(selected, 1):
            case_id = f'case-{serial:03d}'
            folder = reviewer / case_id
            folder.mkdir()
            members = []
            for side, identity in zip(('left', 'right'), pairs[index]):
                unit = units[identity]
                snippet = snippets.read(unit['entry'])
                source = sources.read(unit['path'])
                assert hashlib.sha256(snippet).hexdigest() == unit['sha256']
                assert hashlib.sha256(source).hexdigest() == unit['source_sha256']
                (folder / f'{side}-snippet.rs').write_bytes(snippet)
                (folder / f'{side}-source.rs').write_bytes(source)
                (folder / f'{side}-doc.txt').write_text(bindings[identity])
                members.append({key: unit[key] for key in ('id', 'path', 'package', 'name', 'start_line', 'end_line', 'range', 'sha256', 'source_sha256')})
            cases.append({'case_id': case_id, 'members': members, 'assessment': {field: None for field in protocol['review_fields']}})
            component = {}
            for method in ('code', 'documentation'):
                rank = rank_maps[method].get(index)
                value = float(scores[method][index])
                complete_rank = 1 + sum(float(other) > value or (float(other) == value and position < index) for position, other in enumerate(scores[method]))
                component[method] = {'score': value, 'complete_rank': complete_rank, 'positive_rank': rank, 'tie_group_size': tie_counts[method][value], 'complete_contribution': 1 / (60 + complete_rank), 'positive_contribution': 0 if rank is None else 1 / (60 + rank)}
            analyst.append({'case_id': case_id, 'unit_ids': pairs[index], 'component': component, 'method_ranks': {method: ranks.get(index) for method, ranks in rank_maps.items()}, 'category': 'absent_text' if any(not bindings[identity].strip() for identity in pairs[index]) else ('present_zero' if scores['documentation'][index] == 0 else 'present_positive')})
    dump(reviewer / 'cases.json', cases)
    dump(run / 'analyst-only.json', analyst)
    summary = {'cases_prepared': len(cases), 'cases_reviewed': 0, 'pair_categories': dict(categories), 'positive_only_zero_doc_upper_bound': 1 / 61, 'complete_zero_doc_upper_bound': 1 / 61 + 1 / (60 + documents_positive + 1), 'rrf_cutoff': report['methods']['rrf_complete']['cutoff'], 'limitations': ['No independent judgments obtained', 'Method-hidden presentation, not access control', 'No held-out generalization or relevance scores']}
    assert summary['complete_zero_doc_upper_bound'] < summary['rrf_cutoff']
    summary['artifacts_sha256'] = {str(path.relative_to(run)): sha(path) for path in sorted(run.rglob('*')) if path.is_file()}
    dump(run / 'report.json', summary)
    print(json.dumps({key: value for key, value in summary.items() if key != 'artifacts_sha256'}, indent=2))


if __name__ == '__main__':
    main()
