"""Recompute archived LDA candidate scores without the runner ranking helper."""

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    identities = json.loads((args.run / 'eligible-ids.json').read_text())
    rankings = json.loads((args.run / 'rankings.json').read_text())
    ties = {}
    for seed in json.loads((args.run / 'protocol.json').read_text())['seeds']:
        values = np.load(args.run / f'model-{seed}.npz')['distributions']
        norm = np.sqrt(np.sum(values * values, axis=1))
        similarities = (values @ values.T) / np.outer(norm, norm)
        candidates = []
        for left in range(len(identities)):
            for right in range(left + 1, len(identities)):
                score = round(float(similarities[left, right]), 12)
                candidates.append([score, identities[left], identities[right]])
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        assert candidates[:20] == rankings[str(seed)]
        cutoff = candidates[19][0]
        ties[str(seed)] = {
            'cutoff': cutoff,
            'pairs_at_cutoff': sum(item[0] == cutoff for item in candidates),
            'pairs_above_cutoff': sum(item[0] > cutoff for item in candidates),
            'pairs_rounded_to_one': sum(item[0] == 1 for item in candidates),
        }
    root = Path(__file__).resolve().parents[1]
    old = json.loads((root / 'research/evidence/runs/2026-11-09-doc-tfidf-01/review-queue.json').read_text())
    assert [entry[1:] for entry in rankings['tfidf']] == [entry['unit_ids'] for entry in old]
    report = {'independent_cosine_and_ranking': 'all three seeds passed', 'tfidf_pairs_match_original': True, 'posthoc_tie_diagnostic': ties}
    (args.run / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
