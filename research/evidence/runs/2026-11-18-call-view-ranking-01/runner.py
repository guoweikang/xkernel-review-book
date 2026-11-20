"""Compare unresolved call-spelling views on the frozen common population."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def identity(value):
    return value


def features(record):
    sites = record['sites'] if record['status'] == 'parsed' else []
    allowed = {'call_expression', 'method_expression'}
    tokens = [json.dumps([site['kind'], site['deferred_depth'], site['name']],
                        ensure_ascii=False) if site['kind'] in allowed and site['name'] else None
              for site in sites]
    unigrams = sorted({'U:' + token for token in tokens if token is not None})
    adjacent = {'B:' + json.dumps([tokens[index], tokens[index + 1]], ensure_ascii=False)
                for index in range(len(tokens) - 1)
                if tokens[index] is not None and tokens[index + 1] is not None
                and sites[index]['deferred_depth'] == sites[index + 1]['deferred_depth']}
    return {'call_set': unigrams, 'call_order': sorted(set(unigrams) | adjacent)}


def vectorize(documents):
    return TfidfVectorizer(analyzer=identity, binary=True, norm='l2', smooth_idf=True,
                          sublinear_tf=False, use_idf=True).fit_transform(documents)


def controls():
    documents = [['a', 'b', 'b'], ['a', 'b'], ['c'], []]
    actual = vectorize(documents).toarray()
    expected = []
    for document in documents:
        weights = [math.log(5 / (1 + sum(token in item for item in documents))) + 1
                   if token in document else 0 for token in ['a', 'b', 'c']]
        norm = math.sqrt(sum(weight ** 2 for weight in weights))
        expected.append([weight / norm if norm else 0 for weight in weights])
    np.testing.assert_allclose(actual, expected, atol=1e-12)
    assert np.isclose(actual[0] @ actual[1], 1) and actual[0] @ actual[2] == 0
    assert not actual[3].any()
    sites = [{'kind': 'method_expression', 'deferred_depth': 0, 'name': name}
             for name in ['first', 'second']]
    forward = features({'status': 'parsed', 'sites': sites})
    reverse = features({'status': 'parsed', 'sites': list(reversed(sites))})
    assert forward['call_set'] == reverse['call_set']
    assert forward['call_order'] != reverse['call_order']
    barrier = {'kind': 'opaque_macro', 'deferred_depth': 0, 'name': 'hidden'}
    blocked = features({'status': 'parsed', 'sites': [sites[0], barrier, sites[1]]})
    assert blocked['call_order'] == forward['call_set']
    assert features({'status': 'rejected', 'sites': sites})['call_set'] == []
    return 'binary-idf-cosine, identical/disjoint/empty, order, macro barrier and rejected controls passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calls', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert sklearn.__version__ == '1.7.2'
    control = controls()
    scope = RUNS / '2026-11-16-discovery-common-scope-01/protocol.json'
    inputs = json.loads(scope.read_text())['inputs']
    for name in ('units', 'tokens'):
        assert digest(ROOT / inputs[name]['path']) == inputs[name]['sha256']
    units = {row['id']: row for row in json.loads((ROOT / inputs['units']['path']).read_text())}
    token_rows = json.loads((ROOT / inputs['tokens']['path']).read_text())['records']
    eligible = sorted(row['unit_id'] for row in token_rows if row['size_eligible'])
    payload = json.loads(args.calls.read_text())
    records = payload['records'] if isinstance(payload, dict) else payload
    by_id = {row['unit_id']: row for row in records}
    assert len(by_id) == len(records) == len(eligible) == 812 and set(by_id) == set(eligible)
    for row in records:
        assert row['source_sha256'] == units[row['unit_id']]['sha256']
        for site in row['sites']:
            assert site['target_resolution'] == 'unresolved'
    representations = {unit: features(by_id[unit]) for unit in eligible}
    baseline = RUNS / '2026-11-16-common-budget-01'
    code_top = {tuple(row[1:]) for row in json.loads((baseline / 'code-top100.json').read_text())[:20]}
    doc_top = {tuple(row[1:]) for row in json.loads((baseline / 'documentation-top100.json').read_text())[:20]}
    scc_path = RUNS / '2026-11-05-rust-scc-01/candidates.json'
    scc = {tuple(sorted(member['id'] for member in row['members'])) for row in json.loads(scc_path.read_text())}
    ledger_path = ROOT / 'research/protocols/discovery-ledger-v4.json'
    reviewed = {tuple(sorted(member['id'] for member in row['members']))
                for row in json.loads(ledger_path.read_text())['records'] if row['review_status'] == 'reviewed'}
    doc_queue = RUNS / '2026-11-09-doc-tfidf-01/review-queue.json'
    reviewed.update(tuple(sorted(row['unit_ids'])) for row in json.loads(doc_queue.read_text()))
    args.output.mkdir(parents=True, exist_ok=False)
    protocol = ROOT / 'research/protocols/call-view-discovery-v1.json'
    shutil.copy2(protocol, args.output / 'protocol.json')
    shutil.copy2(__file__, args.output / 'runner.py')
    all_rankings = {}
    summaries = {}
    for method in ('call_set', 'call_order'):
        documents = [representations[unit][method] for unit in eligible]
        vectors = vectorize(documents)
        similarities = (vectors @ vectors.T).toarray()
        ranked = []
        for left, right in itertools.combinations(range(len(eligible)), 2):
            score = round(float(similarities[left, right]), 12)
            if score > 0:
                ranked.append([score, eligible[left], eligible[right]])
        ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
        all_rankings[method] = ranked
        top = {tuple(row[1:]) for row in ranked[:20]}
        diagnostics = []
        for score, first, second in ranked[:20]:
            shared = set(representations[first][method]) & set(representations[second][method])
            diagnostics.append({'pair': [first, second], 'score': score, 'shared_features': len(shared),
                                'feature_sizes': [len(representations[unit][method]) for unit in (first, second)],
                                'names': [units[unit]['name'] for unit in (first, second)],
                                'paths': [units[unit]['path'] for unit in (first, second)]})
        summaries[method] = {'positive_pairs': len(ranked), 'nonzero_units': sum(bool(row) for row in documents),
                             'features': vectors.shape[1], 'code_top20_overlap': len(top & code_top),
                             'doc_top20_overlap': len(top & doc_top), 'full_scc_overlap': len(top & scc),
                             'previous_review_overlap': len(top & reviewed),
                             'cutoff_score': ranked[19][0], 'cutoff_ties': sum(row[0] == ranked[19][0] for row in ranked),
                             'ranking_sha256': hashlib.sha256(json.dumps(ranked).encode()).hexdigest()}
        dump(args.output / (method + '-top100.json'), ranked[:100])
        dump(args.output / (method + '-diagnostics.json'), diagnostics)
    selected = []
    seen = set()
    for rank in range(20):
        for method in ('call_set', 'call_order'):
            row = all_rankings[method][rank]
            pair = tuple(row[1:])
            if pair in seen or pair in code_top or pair in reviewed:
                continue
            seen.add(pair)
            selected.append({'pair': list(pair), 'selected_from': method, 'rank': rank + 1,
                             'members': [units[unit] for unit in pair], 'reference_label': None})
            if len(selected) == 6:
                break
        if len(selected) == 6:
            break
    dump(args.output / 'review-queue.json', selected)
    dump(args.output / 'features.json', representations)
    freeze_paths = [scope, args.calls, protocol, Path(__file__), ledger_path, scc_path, doc_queue,
                    baseline / 'code-top100.json', baseline / 'documentation-top100.json']
    dump(args.output / 'freeze.json', {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path): digest(path)
                                     for path in freeze_paths})
    report = {'controls': control, 'units': len(eligible), 'possible_pairs': 329266,
              'parse_status': dict(Counter(row['status'] for row in records)),
              'resolved_call_edges': 0, 'methods': summaries, 'selected_review_pairs': len(selected),
              'effectiveness': 'not_measured', 'sklearn_version': sklearn.__version__}
    dump(args.output / 'report.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
