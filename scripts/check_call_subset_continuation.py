"""Validate continuation selection against its audited amendment and source packets."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
RUN = RUNS / '2026-11-18-call-subset-continuation-02'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen = read(RUN / 'freeze.json')
    for name, digest in frozen['files'].items():
        assert sha(ROOT / name) == digest, name
    assert sha(RUN / 'selection.json') == frozen['selection_sha256']
    selection = read(RUN / 'selection.json')
    audit = read(RUNS / '2026-11-18-call-subset-continuation-audit-01/exclusion-input.json')
    queue = selection['queue']
    assert [{key: row[key] for key in ('slot', 'method', 'rank', 'pair')} for row in queue] == audit['recomputation']['queues']['amended']
    assert len(queue) == len({tuple(row['pair']) for row in queue})
    banned = {tuple(row['pair']) for row in audit['excluded_pairs']}
    closed = set(selection['closed_unit_ids'])
    for row in queue:
        assert tuple(row['pair']) not in banned
        assert not closed.intersection(row['pair'])
        assert 1 <= row['rank'] <= 20
        assert row['excluded_by'] == []
    cases = read(RUN / 'reviewer/cases.json')
    hashes = read(RUN / 'package-hashes.json')
    for name, digest in hashes.items():
        assert sha(RUN / name) == digest, name
    assert [case['case_id'] for case in cases] == [row['case_id'] for row in queue]
    members = 0
    for case, row in zip(cases, queue):
        assert [member['id'] for member in case['members']] == row['pair']
        assert not {'rank', 'method', 'score', 'selected_from'}.intersection(case)
        for member in case['members']:
            assert not {'rank', 'method', 'score', 'selected_from'}.intersection(member)
            source = (RUN / 'reviewer' / member['source_file']).read_bytes()
            snippet = (RUN / 'reviewer' / member['snippet_file']).read_bytes()
            assert hashlib.sha256(source).hexdigest() == member['source_sha256']
            assert hashlib.sha256(snippet).hexdigest() == member['sha256']
            start, end = member['range']
            assert source[start:end] == snippet
            assert source[:start].count(b'\n') + 1 == member['start_line']
            assert source[:end-1].count(b'\n') + 1 == member['end_line']
            members += 1
    report = {'cases': len(cases), 'verified_source_members': members,
              'audited_selection_equal': True, 'frozen_hashes_valid': True,
              'no_method_rank_score_fields_in_case_metadata': True,
              'history_completeness_or_semantic_truth_proven': False}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
