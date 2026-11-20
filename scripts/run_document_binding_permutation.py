import argparse
import gzip
import itertools
import json
from pathlib import Path
import platform
import random
import shutil

import numpy as np
import scipy
from scipy import sparse
import sklearn

from prepare_rust_token_bags import decode_bag
from run_doc_tfidf import ROOT, make_vectorizer, rank_pairs, sha


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/document-binding-permutation-v1.json'
    protocol = json.loads(protocol_path.read_text())
    scope = ROOT / 'research/evidence/runs/2026-11-16-discovery-common-scope-01'
    inputs = json.loads((scope / 'protocol.json').read_text())['inputs']
    for info in inputs.values():
        assert sha(ROOT / info['path']) == info['sha256']
    parent = ROOT / 'research/evidence/runs' / protocol['parent']
    tokens = json.loads((ROOT / inputs['tokens']['path']).read_text())['records']
    by_id = {row['unit_id']: row for row in tokens}
    eligible = sorted(row['unit_id'] for row in tokens if row['size_eligible'])
    assert len(eligible) == 812
    assert set(eligible) == {row['unit_id'] for row in json.loads((scope / 'units.json').read_text()) if row['code_eligible']}
    bindings = sorted(json.loads((ROOT / inputs['docs']['path']).read_text()), key=lambda row: row['unit_id'])
    assert len(bindings) == 2180
    bags_path = ROOT / 'research/evidence/runs/2026-11-05-rust-token-bags-01/blocks.file'
    parent_freeze = json.loads((parent / 'freeze.json').read_text())
    assert sha(bags_path) == parent_freeze['bags']
    for helper, expected in parent_freeze['helpers'].items():
        assert sha(ROOT / 'scripts' / helper) == expected
    bags_by_file = {int(line.split(',')[1]): decode_bag(line) for line in bags_path.read_text().splitlines()}
    bags = {identity: bags_by_file[by_id[identity]['file_id']] for identity in eligible}
    for identity in eligible:
        assert sum(bags[identity].values()) == by_id[identity]['tokens']
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    dump(run / 'inputs.json', {'inputs': inputs, 'bags_sha256': sha(bags_path), 'parent_freeze_sha256': sha(parent / 'freeze.json'), 'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}})
    vectorizer = make_vectorizer(json.loads((ROOT / inputs['doc_protocol']['path']).read_text()))
    matrix = vectorizer.fit_transform([row['doc_text'] for row in bindings])
    indices = {row['unit_id']: index for index, row in enumerate(bindings)}
    selected = matrix[[indices[identity] for identity in eligible]].tocsr()
    sparse.save_npz(run / 'native-vectors.npz', selected)
    dump(run / 'vocabulary.json', vectorizer.get_feature_names_out().tolist())
    np.save(run / 'idf.npy', vectorizer.idf_)
    dump(run / 'eligible.json', eligible)
    nonzero = np.flatnonzero(selected.getnnz(axis=1)).tolist()
    assert len(nonzero) == 200
    permutations = {'native': list(range(812))}
    attempts_by_arm = {'native': 0}
    for seed in protocol['seeds']:
        generator = random.Random(seed)
        for attempt in range(1, 10001):
            shuffled = nonzero.copy()
            generator.shuffle(shuffled)
            if all(target != origin for target, origin in zip(nonzero, shuffled)):
                break
        else:
            raise RuntimeError('No derangement within frozen attempt limit')
        mapping = list(range(812))
        for target, origin in zip(nonzero, shuffled):
            mapping[target] = origin
        arm = f'seed-{seed}'
        permutations[arm] = mapping
        attempts_by_arm[arm] = attempt
    dump(run / 'permutations.json', {arm: {'attempts': attempts_by_arm[arm], 'destination_to_source': [{'destination': eligible[index], 'source': eligible[source_index]} for index, source_index in enumerate(mapping)]} for arm, mapping in permutations.items()})
    dump(run / 'freeze.json', {path.name: sha(path) for path in sorted(run.iterdir()) if path.is_file()})
    code = np.zeros((812, 812))
    for left, right in itertools.combinations(range(812), 2):
        first, second = eligible[left], eligible[right]
        score = sum((bags[first] & bags[second]).values()) / max(by_id[first]['tokens'], by_id[second]['tokens'])
        code[left, right] = code[right, left] = score
    document = (selected @ selected.T).toarray()
    np.savez_compressed(run / 'score-matrices.npz', code=code, document=document)
    code_ranking = rank_pairs(eligible, code)
    assert [list(row) for row in code_ranking[:100]] == json.loads((parent / 'code-top100.json').read_text())
    queue = json.loads((parent / 'review-queue.json').read_text())
    anchors = {str(index): tuple(queue[index]['unit_ids']) for index in (7, 27)}
    summaries = {}
    native_top = {}
    upper = np.triu_indices(812, 1)
    reference_scores = np.sort(document[upper])
    for arm, mapping in permutations.items():
        output = run / arm
        output.mkdir()
        assert sorted(mapping) == list(range(812))
        assert all(mapping[index] == index for index in range(812) if index not in nonzero)
        if arm != 'native':
            assert all(mapping[index] != index for index in nonzero)
        doc = document[np.ix_(mapping, mapping)]
        np.testing.assert_array_equal(np.sort(doc[upper]), reference_scores)
        changed = int(np.count_nonzero((selected[mapping] - selected).getnnz(axis=1)))
        summary = {'changed_document_vectors': changed, 'unchanged_nonzero_vectors': 200 - changed, 'methods': {}}
        for method, scores in [('documentation', doc), ('fusion', (code + doc) / 2)]:
            rows = rank_pairs(eligible, scores)
            if arm == 'native':
                assert [list(row) for row in rows[:100]] == json.loads((parent / f'{method}-top100.json').read_text())
            with gzip.open(output / f'{method}-ranking.tsv.gz', 'wt', encoding='utf-8') as handle:
                for score, first, second in rows:
                    handle.write(f'{score:.12f}\t{first}\t{second}\n')
            dump(output / f'{method}-top100.json', rows[:100])
            top = {tuple(row[1:]) for row in rows[:20]}
            if arm == 'native':
                native_top[method] = top
            cutoff = rows[19][0]
            ranks = {tuple(row[1:]): index + 1 for index, row in enumerate(rows)}
            summary['methods'][method] = {'positive_pairs': len(rows), 'cutoff': cutoff, 'above_cutoff': sum(row[0] > cutoff for row in rows), 'at_cutoff': sum(row[0] == cutoff for row in rows), 'native_top20_intersection': len(top & native_top[method]), 'removed_from_native_top20': sorted(native_top[method] - top), 'added_to_native_top20': sorted(top - native_top[method]), 'development_anchor_ranks': {name: ranks.get(pair) for name, pair in anchors.items()}}
        summaries[arm] = summary
    report = {'eligible': 812, 'nonzero_document_positions': 200, 'zero_document_positions': 612, 'native_top100_matches_parent': True, 'document_score_multisets_unchanged': True, 'arms': summaries, 'effectiveness': 'not_measured', 'artifacts_sha256': {str(path.relative_to(run)): sha(path) for path in sorted(run.rglob('*')) if path.is_file()}}
    dump(run / 'report.json', report)
    print(json.dumps({arm: {'changed_vectors': summary['changed_document_vectors'], 'overlaps': {method: detail['native_top20_intersection'] for method, detail in summary['methods'].items()}} for arm, summary in summaries.items()}, indent=2))


if __name__ == '__main__':
    main()
