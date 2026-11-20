"""Independently recompute frozen-corpus TF-IDF scores using the standard library."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    folder = ROOT / 'research/evidence/runs' / args.run_id
    plan = json.loads((folder / 'protocol.json').read_text())
    report = json.loads((folder / 'report.json').read_text())
    manifest = json.loads((folder / 'manifest.json').read_text())
    for base, records in [(folder, report['artifact_sha256']), (ROOT, manifest['inputs'])]:
        for path, expected in records.items():
            if hashlib.sha256((base / path).read_bytes()).hexdigest() != expected:
                raise ValueError(f'hash mismatch: {path}')
    corpus = json.loads((ROOT / plan['fit_input']).read_text())
    options = json.loads((ROOT / plan['base_protocol']).read_text())['vectorizer']
    conditions = json.loads((folder / 'inputs.json').read_text())
    audits = []
    checked_scores = 0
    for method, limits in plan['representations'].items():
        def counts(text):
            words = re.findall(options['token_pattern'], text.lower())
            return Counter(' '.join(words[start:start + size])
                           for size in range(limits[0], limits[1] + 1)
                           for start in range(len(words) - size + 1))

        frequencies = Counter()
        for row in corpus:
            frequencies.update(counts(row['doc_text']).keys())

        def weights(text):
            values = {term: count * (math.log((1 + len(corpus)) / (1 + frequencies[term])) + 1)
                      for term, count in counts(text).items() if term in frequencies}
            norm = math.sqrt(sum(value * value for value in values.values()))
            return {term: value / norm for term, value in values.items()} if norm else {}

        for condition, rows in conditions.items():
            result = json.loads((folder / f'{method}-{condition}-1.json').read_text())
            if (folder / f'{method}-{condition}-1.json').read_bytes() != (folder / f'{method}-{condition}-2.json').read_bytes():
                raise ValueError('repeat mismatch')
            for query, ranking in zip(plan['queries'], result['rankings']):
                query_vector = weights(query['text'])
                expected = []
                for row in rows:
                    candidate = weights(row['text'])
                    score = round(sum(value * candidate.get(term, 0) for term, value in query_vector.items()), 12)
                    expected.append({'id': row['id'], 'score': score})
                expected.sort(key=lambda row: (-row['score'], row['id']))
                if expected != ranking['all_scores'] or ranking['top1'] != [row for row in expected if row['score'] > 0][:1]:
                    raise ValueError('independent score or ranking mismatch')
                checked_scores += len(expected)
        for original, altered in zip(conditions['docs_source-revised'], conditions['docs_source-intervention']):
            before, after = counts(original['text']), counts(altered['text'])
            differences = {term for term in before.keys() | after.keys() if before[term] != after[term]}
            retained = sorted(term for term in differences if term in frequencies)
            audits.append({'representation': method, 'packet': original['id'],
                           'changed_feature_types': len(differences),
                           'retained_changed_features': retained,
                           'lost_changed_features': sorted(differences - set(retained)),
                           'identical_vectors': weights(original['text']) == weights(altered['text'])})
    print(json.dumps({'independently_recomputed_scores': checked_scores,
                      'repeat_verified': True, 'feature_changes': audits}, indent=2))


if __name__ == '__main__':
    main()
