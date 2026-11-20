"""Run frozen common-population code/document rankings without truth labels."""

import argparse
import itertools
import json
from pathlib import Path
import shutil

from prepare_rust_token_bags import decode_bag
from run_doc_tfidf import ROOT, make_vectorizer, sha


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    protocol = ROOT / 'research/protocols/common-budget-ranking-v1.json'
    scope = ROOT / 'research/evidence/runs/2026-11-16-discovery-common-scope-01'
    inputs = json.loads((scope / 'protocol.json').read_text())['inputs']
    for info in inputs.values():
        assert sha(ROOT / info['path']) == info['sha256']
    tokens = json.loads((ROOT / inputs['tokens']['path']).read_text())['records']
    bindings = sorted(json.loads((ROOT / inputs['docs']['path']).read_text()), key=lambda row: row['unit_id'])
    source_units = json.loads((ROOT / inputs['units']['path']).read_text())
    bags_path = ROOT / 'research/evidence/runs/2026-11-05-rust-token-bags-01/blocks.file'
    bags_by_file = {int(line.split(',')[1]): decode_bag(line) for line in bags_path.read_text().splitlines()}
    eligible = sorted(row['unit_id'] for row in tokens if row['size_eligible'])
    assert set(eligible) == {row['unit_id'] for row in json.loads((scope / 'units.json').read_text()) if row['code_eligible']}
    by_id = {row['unit_id']: row for row in tokens}
    bags = {identity: bags_by_file[by_id[identity]['file_id']] for identity in eligible}
    for identity in eligible:
        assert sum(bags[identity].values()) == by_id[identity]['tokens']
    original_pairs_path = ROOT / 'research/evidence/runs/2026-11-05-rust-scc-01/candidates.json'
    original_pairs = {tuple(sorted(member['id'] for member in pair['members'])) for pair in json.loads(original_pairs_path.read_text())}
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(protocol, args.output / 'protocol.json')
    shutil.copy2(__file__, args.output / 'runner.py')
    dump(args.output / 'freeze.json', {'protocol': sha(protocol), 'runner': sha(Path(__file__)),
        'scope_protocol': sha(scope / 'protocol.json'), 'bags': sha(bags_path), 'original_pairs': sha(original_pairs_path),
        'helpers': {name: sha(ROOT / 'scripts' / name) for name in ['run_doc_tfidf.py', 'prepare_rust_token_bags.py']}})
    matrix = make_vectorizer(json.loads((ROOT / inputs['doc_protocol']['path']).read_text())).fit_transform([row['doc_text'] for row in bindings])
    indices = {row['unit_id']: index for index, row in enumerate(bindings)}
    selected = matrix[[indices[identity] for identity in eligible]]
    similarities = (selected @ selected.T).toarray()
    nonzero = {identity for identity, count in zip(eligible, selected.getnnz(axis=1)) if count}
    rankings = {name: [] for name in ['code', 'documentation', 'fusion']}
    threshold_pairs = set()
    for left, right in itertools.combinations(range(len(eligible)), 2):
        first, second = eligible[left], eligible[right]
        shared = sum((bags[first] & bags[second]).values())
        denominator = max(by_id[first]['tokens'], by_id[second]['tokens'])
        code = shared / denominator
        documentation = float(similarities[left, right])
        if shared * 10 >= denominator * 8:
            threshold_pairs.add((first, second))
        for name, score in [('code', code), ('documentation', documentation), ('fusion', (code + documentation) / 2)]:
            rounded = round(score, 12)
            if rounded > 0:
                rankings[name].append([rounded, first, second])
    assert threshold_pairs == original_pairs
    summaries = {}
    for name, rows in rankings.items():
        rows.sort(key=lambda row: (-row[0], row[1], row[2]))
        cutoff = rows[19][0]
        summaries[name] = {'positive_pairs': len(rows), 'cutoff': cutoff,
            'at_cutoff': sum(row[0] == cutoff for row in rows), 'above_cutoff': sum(row[0] > cutoff for row in rows),
            'top20_both_docs': sum(first in nonzero and second in nonzero for _, first, second in rows[:20])}
        dump(args.output / f'{name}-top100.json', rows[:100])
    top = {name: {tuple(row[1:]) for row in rows[:20]} for name, rows in rankings.items()}
    union = sorted(set.union(*top.values()))
    units = {row['id']: row for row in source_units}
    dump(args.output / 'review-queue.json', [{'unit_ids': pair, 'methods': [name for name in top if pair in top[name]],
        'members': [units[identity] for identity in pair], 'truth': 'unknown'} for pair in union])
    report = {'eligible_units': len(eligible), 'nonzero_document_units': len(nonzero),
        'possible_pairs': len(eligible) * (len(eligible) - 1) // 2,
        'original_scc_pairs_recovered': len(threshold_pairs), 'union_top20': len(union),
        'intersections': {f'{left}:{right}': len(top[left] & top[right]) for left, right in itertools.combinations(top, 2)},
        'methods': summaries, 'effectiveness': 'not_measured',
        'artifact_sha256': {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}}
    dump(args.output / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}))


if __name__ == '__main__':
    main()
