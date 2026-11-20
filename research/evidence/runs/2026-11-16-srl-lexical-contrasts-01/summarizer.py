"""Describe all matched lexical contrasts without fitting or changing a rule."""

import hashlib
import itertools
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1] / 'research/evidence/runs'
    frozen = root / '2026-11-16-srl-lexical-inputs-01'
    inference = root / '2026-11-16-srl-lexical-smoke-01'
    results = root / '2026-11-16-srl-lexical-ablation-01'
    output = root / '2026-11-16-srl-lexical-contrasts-01'
    output.mkdir()
    cases = json.loads((frozen / 'cases.json').read_text())
    assert {tuple(case['levels']) for case in cases} == set(itertools.product((0, 1), repeat=4))
    batches = json.loads((inference / 'raw-1.json').read_text())
    frames = {identity: value for batch in batches for identity, value in zip(batch['ids'], batch['output']['srl'], strict=True)}
    decisions = json.loads((results / 'result-1.json').read_text())['rows']['both']
    by_id = {row['id']: row for row in decisions}
    rows = []
    for case in cases:
        targets = [frame for frame in frames[case['id']] if any(role[0] == 'releases' and role[1] == 'PRED' for role in frame)]
        assert len(targets) == 1
        modifiers = [role for role in targets[0] if role[1] in {'ARGM-ADV', 'ARGM-MOD', 'ARGM-CND'}]
        assert bool(modifiers) == by_id[case['id']]['modified']
        rows.append(dict(id=case['id'], levels=case['levels'], modifiers=modifiers,
                         prediction=by_id[case['id']]['prediction']))
    indexed = {tuple(row['levels']): row for row in rows}
    contrasts = []
    for factor in range(4):
        pairs = []
        for levels, baseline in indexed.items():
            if levels[factor] != 0:
                continue
            changed = list(levels)
            changed[factor] = 1
            variant = indexed[tuple(changed)]
            pairs.append({'base': baseline['id'], 'variant': variant['id'],
                          'modifier_delta': int(bool(variant['modifiers'])) - int(bool(baseline['modifiers']))})
        assert len(pairs) == 8
        contrasts.append({'factor': factor, 'pairs': pairs,
                          'net_attachment_delta': sum(pair['modifier_delta'] for pair in pairs)})
    report = {'rows': rows, 'contrasts': contrasts,
              'attached': sum(bool(row['modifiers']) for row in rows),
              'false_positive': sum(row['prediction'] == 'positive' for row in rows),
              'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [frozen / 'cases.json', inference / 'raw-1.json', results / 'result-1.json']}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'summarizer.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
