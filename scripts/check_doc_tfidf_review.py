"""Join frozen review annotations to source and token eligibility; not a semantic oracle."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_annotations(records, queue):
    expected = [pair['rank'] for pair in queue]
    if sorted(item['rank'] for item in records) != expected:
        raise ValueError('Missing, duplicate or unexpected rank')
    allowed = {'configuration_alternatives', 'contract_difference', 'existing_delegation',
               'small_overlap_benefit_unknown'}
    if any(item['assessment'] not in allowed or not item['finding'] or not item['next']
           for item in records):
        raise ValueError('Invalid annotation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    queue_path = RUNS / '2026-11-09-doc-tfidf-01/review-queue.json'
    queue_report = json.loads((queue_path.parent / 'report.json').read_text())
    if digest(queue_path) != queue_report['artifact_sha256']['review-queue.json']:
        raise ValueError('Queue changed')
    queue = json.loads(queue_path.read_text())
    annotation_path = ROOT / 'research/protocols/doc-tfidf-review-v1.json'
    annotations = json.loads(annotation_path.read_text())['records']
    check_annotations(annotations, queue)
    malformed = [annotations[:-1], annotations + [annotations[0]], copy.deepcopy(annotations)]
    malformed[2][0]['assessment'] = 'proven_optimization'
    for records in malformed:
        try:
            check_annotations(records, queue)
        except ValueError:
            continue
        raise AssertionError('Invalid annotation accepted')
    corpus = RUNS / '2026-11-05-rust-baseline-corpus-01'
    corpus_report = json.loads((corpus / 'report.json').read_text())
    for name in ['units.json', 'units.zip', 'sources.zip']:
        if digest(corpus / name) != corpus_report['artifacts_sha256'][name]:
            raise ValueError('Source corpus changed')
    units = {unit['id']: unit for unit in json.loads((corpus / 'units.json').read_text())}
    tokens_path = RUNS / '2026-11-05-rust-token-bags-01/report.json'
    tokens = {item['unit_id']: item for item in json.loads(tokens_path.read_text())['records']}
    annotation_by_rank = {item['rank']: item for item in annotations}
    records = []
    with zipfile.ZipFile(corpus / 'units.zip') as archive:
        for pair in queue:
            members = []
            for identity in pair['unit_ids']:
                unit = units[identity]
                source = archive.read(unit['entry'])
                if hashlib.sha256(source).hexdigest() != unit['sha256']:
                    raise ValueError('Function identity changed')
                token = tokens[identity]
                if token['path'] != unit['path'] or token['range'] != unit['range']:
                    raise ValueError('Token mapping differs')
                members.append({'unit_id': identity, 'path': unit['path'], 'name': unit['name'],
                                'range': unit['range'], 'sha256': unit['sha256'],
                                'source': source.decode(), 'attributes': unit['attributes'],
                                'tokens': token['tokens'], 'size_eligible': token['size_eligible']})
            records.append({**annotation_by_rank[pair['rank']], 'members': members,
                            'in_scc_outputs': pair['in_scc_outputs'],
                            'review_method': 'single_assistant_static_source_review',
                            'truth_label': None, 'net_benefit': 'unverified'})
    (args.output / 'reviews.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(__file__, args.output / 'checker.py')
    shutil.copyfile(annotation_path, args.output / 'annotations.json')
    report = {'reviewed_pairs': len(records), 'assessment_counts': dict(Counter(
        item['assessment'] for item in records)),
        'scc_overlap': sum(item['in_scc_outputs'] for item in records),
        'both_below_65_tokens': sum(all(member['tokens'] < 65 for member in item['members']) for item in records),
        'both_size_eligible': sum(all(member['size_eligible'] for member in item['members']) for item in records),
        'negative_controls_passed': 3, 'runtime_tests': 'not_run', 'independent_labels': 'not_available',
        'input_sha256': {'queue': digest(queue_path), 'annotations': digest(annotation_path),
                         'tokens': digest(tokens_path), 'corpus_report': digest(corpus / 'report.json')},
        'artifact_sha256': {path.name: digest(path) for path in args.output.iterdir() if path.is_file()}}
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if not key.endswith('sha256')}))


if __name__ == '__main__':
    main()
