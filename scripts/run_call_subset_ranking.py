"""Run the frozen non-test-path-hint, non-nested code/call-set comparison."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
import time

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

from prepare_rust_token_bags import decode_bag


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'research/protocols/call-subset-ranking-v1.json'
METHODS = ('code', 'call_set')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(value):
    return value


def call_features(record):
    if record['status'] != 'parsed':
        return []
    return sorted({'U:' + json.dumps([site['kind'], site['deferred_depth'], site['name']], ensure_ascii=False)
                   for site in record['sites']
                   if site['kind'] in {'call_expression', 'method_expression'} and site['name']})


def vectorize(documents):
    if not any(documents):
        return np.zeros((len(documents), len(documents))), {'vocabulary': [], 'idf': []}
    vectorizer = TfidfVectorizer(analyzer=identity, binary=True, norm='l2', smooth_idf=True,
                                 sublinear_tf=False, use_idf=True)
    vectors = vectorizer.fit_transform(documents)
    return (vectors @ vectors.T).toarray(), {
        'vocabulary': vectorizer.get_feature_names_out().tolist(), 'idf': vectorizer.idf_.tolist(),
    }


def code_score(first, second):
    denominator = max(sum(first.values()), sum(second.values()))
    return sum((first & second).values()) / denominator if denominator else 0.0


def select_streams(streams, slots):
    positions = {method: 0 for method in METHODS}
    selected = []
    unfilled = []
    for number, method in enumerate(slots, 1):
        position = positions[method]
        if position >= len(streams[method]):
            unfilled.append({'slot': number, 'method': method, 'reason': 'exclusive_unexposed_top20_exhausted'})
            continue
        selected.append({'slot': number, 'selected_from': method, **streams[method][position]})
        positions[method] += 1
    return selected, unfilled


def controls():
    documents = [['a', 'b', 'b'], ['a', 'b'], ['c'], []]
    actual, _ = vectorize(documents)
    expected = []
    for document in documents:
        weights = [math.log(5 / (1 + sum(token in item for item in documents))) + 1
                   if token in document else 0 for token in ['a', 'b', 'c']]
        norm = math.sqrt(sum(weight ** 2 for weight in weights))
        expected.append([weight / norm if norm else 0 for weight in weights])
    expected = np.array(expected)
    np.testing.assert_allclose(actual, expected @ expected.T, atol=1e-12)
    require(code_score(Counter({'a': 2, 'b': 1}), Counter({'a': 1, 'c': 1})) == 1 / 3, 'Code multiset formula')
    require(code_score(Counter(), Counter()) == 0, 'Empty code control')
    sites = [{'kind': 'method_expression', 'name': 'read', 'deferred_depth': depth} for depth in (0, 1)]
    sites += [{'kind': 'opaque_macro', 'name': 'hidden', 'deferred_depth': 0},
              {'kind': 'call_expression', 'name': None, 'deferred_depth': 0}]
    require(len(call_features({'status': 'parsed', 'sites': sites})) == 2, 'Feature filtering/deferred control')
    require(call_features({'status': 'rejected', 'sites': sites}) == [], 'Rejected zero row')
    empty, metadata = vectorize([[], [], []])
    require(empty.shape == (3, 3) and not empty.any() and metadata['vocabulary'] == [], 'Empty vocabulary')
    picked, missing = select_streams({'call_set': [], 'code': [{'pair': ['a', 'b'], 'rank': 1}]},
                                     ['call_set', 'code', 'call_set', 'code', 'call_set', 'code'])
    require(len(picked) == 1 and picked[0]['slot'] == 2 and len(missing) == 5, 'No fallback on exhaustion')
    return {'independent_binary_idf_cosine': True, 'code_multiset_formula': True,
            'feature_and_reject_controls': True, 'empty_vocabulary': True, 'selection_underfill': True}


def verify_original_freezes(protocol):
    for info in list(protocol['inputs'].values()) + protocol['source_freeze_checks']:
        require(sha(ROOT / info['path']) == info['sha256'], 'Frozen input changed: ' + info['path'])
    baseline = ROOT / 'research/evidence/runs/2026-11-16-common-budget-01'
    freeze = read(baseline / 'freeze.json')
    paths = {
        'runner': ROOT / 'scripts/run_common_budget_ranking.py',
        'protocol': ROOT / 'research/protocols/common-budget-ranking-v1.json',
        'scope_protocol': ROOT / protocol['inputs']['scope_protocol']['path'],
        'bags': ROOT / protocol['inputs']['bags']['path'],
        'original_pairs': ROOT / 'research/evidence/runs/2026-11-05-rust-scc-01/candidates.json',
    }
    checks = {key: sha(path) == freeze[key] for key, path in paths.items()}
    checks.update({name: sha(ROOT / 'scripts' / name) == digest for name, digest in freeze['helpers'].items()})
    old_calls = read(ROOT / 'research/evidence/runs/2026-11-18-call-view-ranking-01/freeze.json')
    name = 'scripts/run_call_view_discovery.py'
    checks['original_call_view_runner'] = sha(ROOT / name) == old_calls[name]
    require(all(checks.values()), 'Original code/source freeze failed: ' + str(checks))
    return checks


def cutoffs(ranked, budget):
    if len(ranked) < budget:
        return {'budget': budget, 'selected': len(ranked), 'cutoff': None, 'at_cutoff': 0,
                'above_cutoff': 0, 'selected_at_cutoff': 0, 'ties_beyond_budget': 0}
    cutoff = ranked[budget - 1][0]
    above = sum(row[0] > cutoff for row in ranked)
    tied = sum(row[0] == cutoff for row in ranked)
    return {'budget': budget, 'selected': budget, 'cutoff': cutoff, 'at_cutoff': tied,
            'above_cutoff': above, 'selected_at_cutoff': budget - above,
            'ties_beyond_budget': tied - (budget - above)}


def compare_runs(first, second):
    telemetry = {'environment.json', 'timings.json', 'artifact-hashes.json', 'repeat-check.json'}
    def hashes(directory):
        return {path.name: sha(path) for path in directory.iterdir() if path.is_file() and path.name not in telemetry}
    previous, current = hashes(first), hashes(second)
    require(previous == current, 'Deterministic artifacts differ between isolated runs')
    np.testing.assert_array_equal(np.load(first / 'pair-scores.npy'), np.load(second / 'pair-scores.npy'))
    return {'passed': True, 'first_run': first.name, 'second_run': second.name,
            'compared_artifacts': previous, 'full_score_arrays_equal': True,
            'excluded_telemetry': sorted(telemetry),
            'timings': {first.name: read(first / 'timings.json'), second.name: read(second / 'timings.json')},
            'performance_conclusion': 'not_established'}


def run(output, compare_with):
    started = time.monotonic()
    require(not output.exists(), 'Refusing to overwrite existing output')
    protocol = read(PROTOCOL)
    require(sklearn.__version__ == protocol['execution']['sklearn_version'], 'Wrong sklearn version')
    require(np.__version__ == protocol['execution']['numpy_version'], 'Wrong numpy version')
    freeze_checks = verify_original_freezes(protocol)
    control_results = controls()
    inputs = {name: ROOT / info['path'] for name, info in protocol['inputs'].items()}
    scope = read(inputs['scope_protocol'])
    for name in ('units', 'tokens'):
        require(protocol['inputs'][name] == scope['inputs'][name], 'Not common-scope input: ' + name)
    units_list = read(inputs['units'])
    units = {row['id']: row for row in units_list}
    token_rows = read(inputs['tokens'])['records']
    token_by_id = {row['unit_id']: row for row in token_rows}
    common = sorted(row['unit_id'] for row in token_rows if row['size_eligible'])
    require(len(common) == len(set(common)) == 812, 'Common population differs')
    require(set(common) == {row['unit_id'] for row in read(inputs['scope_units']) if row['code_eligible']}, 'Scope IDs differ')
    for identity_value in common:
        require(type(units[identity_value]['test_path_hint']) is bool and
                type(units[identity_value]['nested_in_function']) is bool, 'Missing/invalid population hints')
    eligible = [identity_value for identity_value in common
                if not units[identity_value]['test_path_hint'] and not units[identity_value]['nested_in_function']]
    require(len(eligible) == protocol['population']['expected_subset'] == 429, 'Unexpected subset')
    payload = read(inputs['calls'])
    records = payload['records'] if isinstance(payload, dict) else payload
    calls = {row['unit_id']: row for row in records}
    require(len(records) == len(calls) == 812 and set(calls) == set(common), 'Call envelope/population mismatch')
    for identity_value in common:
        record = calls[identity_value]
        require(record['source_sha256'] == units[identity_value]['sha256'], 'Call/source hash mismatch')
        require(hashlib.sha256(record['source_text'].encode()).hexdigest() == record['source_sha256'], 'Call source text changed')
        for site in record['sites']:
            require(site['target_resolution'] == 'unresolved', 'Resolved call assumption')
    bags_by_file = {int(line.split(',')[1]): decode_bag(line) for line in inputs['bags'].read_text().splitlines()}
    bags = {identity_value: bags_by_file[token_by_id[identity_value]['file_id']] for identity_value in eligible}
    for identity_value in eligible:
        require(sum(bags[identity_value].values()) == token_by_id[identity_value]['tokens'], 'Token count mismatch')
    features = {identity_value: call_features(calls[identity_value]) for identity_value in eligible}
    exclusions = {}
    def exclude(pair, reason):
        exclusions.setdefault(tuple(sorted(pair)), []).append(reason)
    for row in read(inputs['scc_review_ledger'])['records']:
        if row['review_status'] == 'reviewed':
            exclude([member['id'] for member in row['members']], 'previously_reviewed_scc_ledger')
    for row in read(inputs['prior_doc_queue']):
        exclude(row['unit_ids'], 'prior_doc_queue_exposure_not_truth')
    original_six = read(inputs['original_six'])
    require(len(original_six) == 6, 'Original six queue changed')
    for row in original_six:
        exclude(row['pair'], 'original_six_reviewed')
    load_elapsed = time.monotonic() - started
    ranking_started = time.monotonic()
    documents = [features[identity_value] for identity_value in eligible]
    cosine, vectorizer = vectorize(documents)
    vectorizer['fit_population'] = len(eligible)
    vectorizer['zero_rows_retained'] = sum(not document for document in documents)
    pairs = list(itertools.combinations(eligible, 2))
    positions = {identity_value: position for position, identity_value in enumerate(eligible)}
    score_array = np.zeros((len(pairs), 2))
    rankings = {method: [] for method in METHODS}
    for pair_index, (first, second) in enumerate(pairs):
        values = [code_score(bags[first], bags[second]), float(cosine[positions[first], positions[second]])]
        for column, method in enumerate(METHODS):
            score = round(values[column], protocol['ranking']['round_decimal_places'])
            score_array[pair_index, column] = score
            if score > 0:
                rankings[method].append([score, first, second])
    for method in METHODS:
        rankings[method].sort(key=lambda row: (-row[0], row[1], row[2]))
    ranking_elapsed = time.monotonic() - ranking_started
    post_started = time.monotonic()
    tops = {method: {tuple(row[1:]) for row in rankings[method][:20]} for method in METHODS}
    streams = {method: [] for method in METHODS}
    selection_ledger = []
    for method in ('call_set', 'code'):
        other = 'code' if method == 'call_set' else 'call_set'
        for rank, row in enumerate(rankings[method][:20], 1):
            pair = tuple(row[1:])
            reasons = list(exclusions.get(pair, []))
            if pair in tops[other]:
                reasons.append('shared_with_other_method_top20')
            selection_ledger.append({'method': method, 'pair': pair, 'rank': rank, 'score': row[0],
                                     'eligible': not reasons, 'blocked_by': reasons})
            if not reasons:
                streams[method].append({'pair': list(pair), 'rank': rank, 'score': row[0]})
    selected, unfilled = select_streams(streams, protocol['review_selection']['slots'])
    for row in selected:
        row['members'] = [units[identity_value] for identity_value in row['pair']]
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(PROTOCOL, output / 'protocol.json')
    shutil.copyfile(__file__, output / 'runner.py')
    shutil.copyfile(inputs['bag_helper'], output / 'bag-helper.py')
    dump(output / 'freeze.json', {'protocol_sha256': sha(PROTOCOL), 'runner_sha256': sha(Path(__file__)),
                                  'inputs': protocol['inputs'], 'source_freeze_checks': protocol['source_freeze_checks'],
                                  'original_source_freezes_passed': freeze_checks})
    dump(output / 'eligible.json', eligible)
    dump(output / 'units.json', [units[identity_value] for identity_value in eligible])
    dump(output / 'subset-selection.json', [{'unit_id': identity_value,
          'test_path_hint': units[identity_value]['test_path_hint'],
          'nested_in_function': units[identity_value]['nested_in_function'],
          'selected': identity_value in positions} for identity_value in common])
    dump(output / 'features.json', [{'unit_id': identity_value, 'parse_status': calls[identity_value]['status'],
                                    'call_set': features[identity_value]} for identity_value in eligible])
    dump(output / 'vectorizer.json', vectorizer)
    np.save(output / 'pair-scores.npy', score_array, allow_pickle=False)
    dump(output / 'pair-score-schema.json', {'rows': 'itertools.combinations(eligible.json, 2)',
                                           'columns': list(METHODS), 'zero_scores_retained': True,
                                           'shape': list(score_array.shape)})
    dump(output / 'review-queue.json', selected)
    dump(output / 'selection-ledger.json', {'top20_decisions': selection_ledger, 'eligible_streams': streams,
                                           'unfilled_slots': unfilled, 'no_below_top20_fallback': True})
    dump(output / 'exclusions.json', [{'pair': pair, 'reasons': reasons} for pair, reasons in sorted(exclusions.items())])
    summaries = {}
    for column, method in enumerate(METHODS):
        ranked = rankings[method]
        for budget in (20, 100):
            dump(output / f'{method}-top{budget}.json', ranked[:budget])
        diagnostics = []
        for score, first, second in ranked[:20]:
            diagnostics.append({'pair': [first, second], 'score': score,
                                'paths': [units[first]['path'], units[second]['path']],
                                'names': [units[first]['name'], units[second]['name']],
                                'same_file': units[first]['path'] == units[second]['path'],
                                'same_package': units[first]['package'] == units[second]['package'],
                                'call_feature_sizes': [len(features[first]), len(features[second])],
                                'shared_call_features': sorted(set(features[first]) & set(features[second])),
                                'shared_code_tokens': sum((bags[first] & bags[second]).values()),
                                'previous_exposure': exclusions.get((first, second), [])})
        dump(output / f'{method}-diagnostics.json', diagnostics)
        summaries[method] = {
            'positive_pairs': len(ranked), 'zero_pairs': int(np.count_nonzero(score_array[:, column] == 0)),
            'top20': cutoffs(ranked, 20), 'top100': cutoffs(ranked, 100),
            'same_file_top20': sum(row['same_file'] for row in diagnostics),
            'same_package_top20': sum(row['same_package'] for row in diagnostics),
            'previous_exposure_top20': sum(bool(row['previous_exposure']) for row in diagnostics),
            'exclusive_top20_before_exclusions': len(tops[method] - tops['call_set' if method == 'code' else 'code']),
            'exclusive_unexposed_top20': len(streams[method]),
            'full_positive_ranking_sha256': hashlib.sha256(json.dumps(ranked).encode()).hexdigest(),
        }
    sites = [site for identity_value in eligible for site in calls[identity_value]['sites']]
    attribute_paths = Counter()
    for identity_value in eligible:
        unit = units[identity_value]
        attributes = unit['attributes'] + unit['file_attributes']
        attributes += [attribute for group in unit['ancestor_attributes'] for attribute in group]
        for attribute in attributes:
            if attribute['path'].split('::')[-1] in {'test', 'def_test', 'cfg', 'cfg_attr'}:
                attribute_paths[attribute['path']] += 1
    report = {
        'status': 'packaging_ready_pending_independent_review', 'common_units': 812, 'units': len(eligible),
        'excluded_units': 812 - len(eligible), 'possible_pairs': len(pairs),
        'parse_status': dict(Counter(calls[identity_value]['status'] for identity_value in eligible)),
        'call_zero_row_ids': [identity_value for identity_value in eligible if not features[identity_value]],
        'call_vocabulary_size': len(vectorizer['vocabulary']), 'resolved_edges': 0,
        'site_kinds': dict(Counter(site['kind'] for site in sites)),
        'deferred_sites': sum(site['deferred_depth'] > 0 for site in sites),
        'null_name_sites': sum(site['name'] is None for site in sites),
        'test_or_cfg_attribute_occurrences': dict(attribute_paths),
        'cfg_states': dict(Counter(units[identity_value]['cfg'] for identity_value in eligible)),
        'methods': summaries, 'top20_intersection': len(tops['code'] & tops['call_set']),
        'selected_review_pairs': len(selected), 'selected_by_method': dict(Counter(row['selected_from'] for row in selected)),
        'selected_same_file_pairs': sum(row['members'][0]['path'] == row['members'][1]['path'] for row in selected),
        'unfilled_slots': unfilled, 'controls': control_results,
        'original_source_freezes_passed': verify_original_freezes(protocol),
        'effectiveness': 'not_measured', 'confirmed_production': False, 'models_run': 0,
        'cases_reviewed_this_batch': 0, 'limits': protocol['limits'], 'stop': protocol['stop'],
    }
    require(len(pairs) == 91806, 'Unexpected pair denominator')
    dump(output / 'report.json', report)
    dump(output / 'environment.json', {'python': sys.version, 'executable': sys.executable,
          'platform': platform.platform(), 'numpy': np.__version__, 'sklearn': sklearn.__version__,
          'command': sys.argv, 'threads': {name: os.environ.get(name) for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')}})
    prior_extraction = read(ROOT / 'research/evidence/runs/2026-11-18-common-call-syntax-01/summary.json')
    dump(output / 'timings.json', {
        'prior_extraction': {'elapsed_seconds': prior_extraction['elapsed_seconds'], 'population': 812,
                             'scope': 'Historical extraction wrapper measurement, not reexecuted or subset-only',
                             'source': 'research/evidence/runs/2026-11-18-common-call-syntax-01/summary.json'},
        'preflight_and_loading_seconds': load_elapsed,
        'ranking_computation_seconds': ranking_elapsed,
        'diagnostics_and_serialization_seconds': time.monotonic() - post_started,
        'total_before_optional_repeat_check_seconds': time.monotonic() - started,
        'performance_claim': 'none; do not sum prior extraction with subset ranking into an end-to-end claim',
    })
    if compare_with is not None:
        dump(output / 'repeat-check.json', compare_runs(compare_with, output))
    dump(output / 'artifact-hashes.json', {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()})
    print(json.dumps({key: report[key] for key in ('status', 'units', 'possible_pairs', 'top20_intersection',
                                                 'selected_review_pairs', 'selected_by_method', 'unfilled_slots',
                                                 'original_source_freezes_passed')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--compare-with', type=Path)
    args = parser.parse_args()
    run(args.output.resolve(), args.compare_with.resolve() if args.compare_with else None)


if __name__ == '__main__':
    main()
