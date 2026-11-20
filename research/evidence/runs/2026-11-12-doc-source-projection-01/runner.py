"""Frozen document/source-summary projection sensitivity on development packets."""

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import platform
import shutil

import numpy as np
import sklearn

from run_doc_tfidf import ROOT, make_vectorizer, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (character.isalnum() or character in '-_') for character in args.run_id):
        raise ValueError('invalid run id')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/doc-source-projection-v1.json'
    plan = json.loads(protocol_path.read_text())
    base_path = ROOT / plan['base_protocol']
    baseline = json.loads(base_path.read_text())
    corpus_path = ROOT / plan['fit_input']
    if sha(corpus_path) != baseline['input_sha256'] or sklearn.__version__ != '1.7.2':
        raise ValueError('wrong corpus or sklearn version')
    corpus = sorted(json.loads(corpus_path.read_text()), key=lambda row: row['unit_id'])
    if len(corpus) != 2180:
        raise ValueError('wrong corpus size')
    claims_path = ROOT / plan['claims_run'] / 'claims.json'
    claims = json.loads(claims_path.read_text())
    claim_protocol_path = ROOT / plan['claims_run'] / 'protocol.json'
    claim_plan = json.loads(claim_protocol_path.read_text())
    inputs = [protocol_path, base_path, corpus_path, claims_path, claim_protocol_path,
              Path(__file__), ROOT / 'scripts/run_doc_tfidf.py']
    packets = {}
    for identity in plan['candidate_ids']:
        path = ROOT / claim_plan['parent_run'] / identity / 'packet.json'
        inputs.append(path)
        packets[identity] = json.loads(path.read_text())
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    conditions = {}
    for projection in plan['projections']:
        for variant in plan['variants']:
            rows = []
            for identity in plan['candidate_ids']:
                texts = []
                selected_ids = []
                if identity != 'firmware-ownership':
                    texts.append(packets[identity]['native_text'])
                for claim in claims:
                    if claim['packet'] != identity or claim['kind'] == 'unknown':
                        continue
                    is_source = claim['kind'] == 'source_observation'
                    if is_source and projection == 'docs':
                        continue
                    if not is_source and identity != 'firmware-ownership':
                        continue
                    text = claim['text']
                    intervention = claim_plan['interventions'][identity]
                    if variant == 'intervention' and claim['id'] == intervention['claim']:
                        text = intervention['text']
                    texts.append(text)
                    selected_ids.append(claim['id'])
                rows.append({'id': identity, 'text': '\n\n'.join(text for text in texts if text),
                             'claim_ids': selected_ids})
            conditions[f'{projection}-{variant}'] = rows
    (output / 'inputs.json').write_text(json.dumps(conditions, indent=2) + '\n')
    comparisons = []
    for representation, ngrams in plan['representations'].items():
        options = copy.deepcopy(baseline)
        options['vectorizer']['ngram_range'] = ngrams
        vectorizer = make_vectorizer(options)
        vectorizer.fit([row['doc_text'] for row in corpus])
        analyzer = vectorizer.build_analyzer()
        vocabulary = vectorizer.vocabulary_
        query_texts = [row['text'] for row in plan['queries']]

        def checked_transform(texts):
            actual = vectorizer.transform(texts).toarray()
            expected = np.zeros_like(actual)
            oov = []
            for index, text in enumerate(texts):
                counts = Counter(analyzer(text))
                for term, count in counts.items():
                    if term in vocabulary:
                        column = vocabulary[term]
                        expected[index, column] = count * vectorizer.idf_[column]
                norm = np.linalg.norm(expected[index])
                if norm:
                    expected[index] /= norm
                oov.append({'feature_occurrences': sum(counts.values()),
                            'oov_occurrences': sum(count for term, count in counts.items() if term not in vocabulary),
                            'zero_vector': not bool(norm)})
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
            return actual, oov

        queries, query_oov = checked_transform(query_texts)
        results = {}
        for repeat in range(1, plan['repeats'] + 1):
            for condition, rows in conditions.items():
                matrix, oov = checked_transform([row['text'] for row in rows])
                scores = queries @ matrix.T
                rankings = []
                for query, values in zip(plan['queries'], scores):
                    ordered = sorted([{'id': row['id'], 'score': round(float(value), 12)}
                                      for row, value in zip(rows, values)], key=lambda row: (-row['score'], row['id']))
                    rankings.append({'query': query['id'], 'all_scores': ordered,
                                     'top1': [row for row in ordered if row['score'] > 0][:1]})
                result = {'representation': representation, 'condition': condition,
                          'features': len(vocabulary), 'query_oov': query_oov,
                          'candidate_oov': dict(zip(plan['candidate_ids'], oov)), 'rankings': rankings}
                path = output / f'{representation}-{condition}-{repeat}.json'
                path.write_text(json.dumps(result, indent=2) + '\n')
                if repeat > 1 and path.read_bytes() != (output / f'{representation}-{condition}-1.json').read_bytes():
                    raise ValueError('repeat differs')
                results[condition] = result
        for variant in plan['variants']:
            left = results[f'docs-{variant}']['rankings']
            right = results[f'docs_source-{variant}']['rankings']
            comparisons.append({'representation': representation, 'variant': variant,
                                'top1_id_changes': sum([row['id'] for row in before['top1']] !=
                                                      [row['id'] for row in after['top1']]
                                                      for before, after in zip(left, right))})
        for projection in plan['projections']:
            before = results[f'{projection}-revised']['rankings']
            after = results[f'{projection}-intervention']['rankings']
            for original, altered in zip(conditions[f'{projection}-revised'], conditions[f'{projection}-intervention']):
                if original['text'] == altered['text']:
                    for old_rank, new_rank in zip(before, after):
                        old = {row['id']: row['score'] for row in old_rank['all_scores']}
                        new = {row['id']: row['score'] for row in new_rank['all_scores']}
                        if old[original['id']] != new[original['id']]:
                            raise ValueError('unchanged candidate score drifted')
    manifest = {'inputs': {str(path.relative_to(ROOT)): sha(path) for path in inputs},
                'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    report = {'conditions_executed': 16, 'queries': 6, 'candidates': 3,
              'repeat_identical': True, 'count_idf_normalization_checked': True,
              'comparisons': comparisons, 'accuracy_measured': False,
              'artifact_sha256': {str(path.relative_to(output)): sha(path) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
