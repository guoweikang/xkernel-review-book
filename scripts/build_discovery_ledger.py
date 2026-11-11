"""Join fixed text candidates and explicit assessments without inferring semantic labels."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    'candidates': 'research/evidence/runs/2026-11-05-rust-scc-01/candidates.json',
    'baseline': 'research/evidence/runs/2026-11-05-rust-scc-01/report.json',
    'batch': 'research/protocols/scc-development-review-batch-v1.json',
    'reviews': 'research/protocols/scc-development-review-results-v1.json',
    'assessments': 'research/protocols/discovery-family-assessments-v1.json',
    'metadata': 'research/protocols/metadata-case-disposition-v1.json',
}


def assemble(data):
    candidates = data['candidates']
    reviewed = {tuple(row['file_ids']): row for row in data['reviews']['records']}
    selected = {tuple(row['candidate']['file_ids']) for row in data['batch']['records']}
    identities = [tuple(pair['file_ids']) for pair in candidates]
    if len(set(identities)) != len(identities) or len(reviewed) != len(data['reviews']['records']):
        raise ValueError('Duplicate pair identity')
    if set(reviewed) != selected or not selected.issubset(identities):
        raise ValueError('Review/batch identities do not match candidates')
    families = dict(data['assessments']['families'])
    if 'followup' in data:
        queued = {tuple(row['file_ids']) for row in data['frozen_queue']['followup']['records']}
        for row in data['followup']['records']:
            key = tuple(row['file_ids'])
            if key in reviewed or key not in queued or key not in identities:
                raise ValueError('Followup review is duplicated or outside frozen queue')
            reviewed[key] = row
        extra = data['followup']['families']
        if set(extra) & set(families):
            raise ValueError('Followup cannot silently overwrite existing family assessments')
        families.update(extra)
    if {row['family'] for row in reviewed.values()} != set(families):
        raise ValueError('Missing or unused family assessment')
    metadata = data['metadata']
    if metadata['disposition'] != 'close_development_experiment_retain_feasible_candidate_defer_adoption':
        raise ValueError('Metadata disposition changed; explicitly reconcile assessments')
    groups = []
    for family, assessment in sorted(families.items()):
        if assessment['benefit'] != 'unverified':
            raise ValueError('New benefit claim requires protocol review')
        for evidence in assessment['evidence']:
            if not (ROOT / evidence).is_file():
                raise ValueError('Missing evidence: ' + evidence)
        members = sorted(list(key) for key, row in reviewed.items() if row['family'] == family)
        groups.append({'family': family, 'pairs': members, **assessment, 'truth_label': None})
    records = []
    for pair in candidates:
        review = reviewed.get(tuple(pair['file_ids']))
        records.append({'file_ids': pair['file_ids'],
                        'members': [{key: member[key] for key in ['id', 'path', 'name', 'start_line', 'end_line', 'test_path_hint']}
                                    for member in pair['members']],
                        'text_similarity': {'shared_tokens': pair['shared_tokens'], 'denominator': pair['denominator']},
                        'review_status': 'reviewed' if review else 'unreviewed',
                        'family': review['family'] if review else None,
                        'disposition': families[review['family']]['disposition'] if review else 'unknown',
                        'truth_label': None})
    summary = {'candidate_pairs': len(records), 'reviewed_pairs': len(reviewed),
               'unreviewed_pairs': len(records) - len(reviewed), 'reviewed_families': len(groups),
               'family_dispositions': dict(sorted(Counter(group['disposition'] for group in groups).items())),
               'net_benefit_confirmed': 0}
    used_members = {member for pair in reviewed for member in pair}
    used_paths = set()
    followup = []
    shortfalls = {}
    for hints in range(3):
        pool = [pair for pair in candidates if tuple(pair['file_ids']) not in reviewed
                and sum(bool(member['test_path_hint']) for member in pair['members']) == hints]
        pool.sort(key=lambda pair: (-pair['denominator'], pair['file_ids']))
        selected_count = 0
        for pair in pool:
            paths = tuple(sorted(member['path'] for member in pair['members']))
            if used_members.intersection(pair['file_ids']) or paths in used_paths:
                continue
            followup.append({'file_ids': pair['file_ids'], 'test_path_hint_count': hints,
                             'review_status': 'unreviewed', 'denominator': pair['denominator']})
            used_members.update(pair['file_ids'])
            used_paths.add(paths)
            selected_count += 1
            if selected_count == 2:
                break
        if selected_count < 2:
            shortfalls[str(hints)] = 2 - selected_count
    if 'followup' in data:
        followup = [{**row, 'review_status': 'reviewed' if tuple(row['file_ids']) in reviewed else 'unreviewed'}
                    for row in data['frozen_queue']['followup']['records']]
        shortfalls = data['frozen_queue']['followup']['quota_shortfalls']
    return {'schema': 'discovery-ledger/1', 'summary': summary, 'families': groups, 'records': records,
            'followup': {'selection': 'For each test-path-hint count 0/1/2 in order, take up to two largest denominator pairs; IDs break ties. Exclude reviewed members and repeated members/path pairs within this batch.',
                         'purpose': 'Bounded development review of larger text overlaps with path diversity; size is not benefit or semantic complexity',
                         'bias': 'Post-output purposive selection, not random, independent or representative',
                         'records': followup, 'quota_shortfalls': shortfalls},
            'limits': ['Family grouping is researcher-assigned, not automatic semantic detection',
                       'Unreviewed pairs remain unknown, not negative or low-value',
                       'Families are maintenance themes, not independent statistical samples',
                       'No precision, recall, probability score or independent truth labels established']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--followup', action='store_true', help='Overlay reviews onto the frozen v1 followup queue')
    parser.add_argument('--followup-results', default='research/protocols/discovery-followup-results-v1.json')
    args = parser.parse_args()
    if args.followup:
        INPUTS['followup'] = args.followup_results
        INPUTS['frozen_queue'] = 'research/protocols/discovery-ledger-v1.json'
    raw = {name: (ROOT / path).read_bytes() for name, path in INPUTS.items()}
    data = {name: json.loads(content) for name, content in raw.items()}
    identity = hashlib.sha256(raw['candidates']).hexdigest()
    if not data['baseline']['passed'] or identity != data['baseline']['artifacts_sha256']['candidates.json'] or identity != data['batch']['candidate_sha256']:
        raise ValueError('Candidate provenance failed')
    result = assemble(data)
    if args.self_check:
        for mutation in ['duplicate', 'missing_review', 'orphan_review', 'missing_family', 'benefit_claim']:
            modified = json.loads(json.dumps(data))
            if mutation == 'duplicate':
                modified['candidates'].append(modified['candidates'][0])
            elif mutation == 'missing_review':
                modified['reviews']['records'].pop()
            elif mutation == 'orphan_review':
                modified['reviews']['records'][0]['file_ids'] = [-1, -2]
            elif mutation == 'missing_family':
                modified['assessments']['families'].pop('pipe_timestamp_wrappers')
            else:
                modified['assessments']['families']['pipe_timestamp_wrappers']['benefit'] = 'proven'
            try:
                assemble(modified)
            except ValueError:
                continue
            raise AssertionError('Accepted invalid join: ' + mutation)
        print('PASS: real ledger assembled; 5 invalid joins/claim controls rejected')
        return
    if args.output is None:
        parser.error('--output or --self-check required')
    result['input_sha256'] = {INPUTS[name]: hashlib.sha256(content).hexdigest() for name, content in raw.items()}
    result['builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
