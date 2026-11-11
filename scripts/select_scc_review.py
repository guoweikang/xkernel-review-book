"""Select a deterministic development review batch, not a blind evaluation set."""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'research/evidence/runs/2026-11-05-rust-scc-01'
    raw = (source / 'candidates.json').read_bytes()
    report = json.loads((source / 'report.json').read_text())
    if not report['passed'] or hashlib.sha256(raw).hexdigest() != report['artifacts_sha256']['candidates.json']:
        raise ValueError('Candidate provenance gate failed')
    candidates = json.loads(raw)
    selected = []
    for hints in range(3):
        group = [pair for pair in candidates if sum(bool(member['test_path_hint']) for member in pair['members']) == hints]
        group.sort(key=lambda pair: (-Fraction(pair['shared_tokens'], pair['denominator']), pair['file_ids']))
        if len(group) < 4:
            raise ValueError('Insufficient records for fixed strata rule')
        for band, pairs in [('highest', group[:2]), ('lowest', group[-2:])]:
            for pair in pairs:
                selected.append({'test_path_hint_count': hints, 'similarity_band': band,
                                 'review_status': 'unreviewed', 'candidate': pair})
    if len({tuple(record['candidate']['file_ids']) for record in selected}) != 12:
        raise ValueError('Repeated pair in review batch')
    output = {'schema': 'scc-development-review-batch/1',
              'selection': 'two highest and two lowest similarity pairs per test-path-hint-count stratum; file IDs break ties',
              'bias': 'post-output purposive selection; not random, blind, independent or representative',
              'candidate_sha256': hashlib.sha256(raw).hexdigest(),
              'selector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'records': selected}
    with args.output.open('x') as stream:
        stream.write(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'selected': len(selected), 'file_ids': [record['candidate']['file_ids'] for record in selected]}))


if __name__ == '__main__':
    main()
