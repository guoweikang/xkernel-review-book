"""Recheck retrieval controls and reject incorrect decomposition assumptions."""

import json
import math
from pathlib import Path
import sys

from run_inmap_retrieval_controls import factor, top
from run_inmap_snapshots import ROOT, RUNS, digest, scores


def main():
    batch = RUNS / sys.argv[1]
    manifest = json.loads((batch / 'manifest.json').read_text())
    assert digest(batch / 'manifest.json') == (batch / 'manifest.sha256').read_text().strip()
    for name, checksum in manifest['sha256'].items():
        assert digest(ROOT / name) == checksum
    assert factor(('org.example.model.Item', 'model')) == 33.0
    assert factor(('org.example.Item', 'model')) == 1.0 / 33.0
    assert factor(('org.example.builder.Item', 'gui ui')) == 33.0
    assert factor(('org.example.Model', 'model')) == 1.0 / 33.0
    try:
        factor(('org.example.Item', 'unknown'))
    except AssertionError:
        pass
    else:
        raise AssertionError('Unsupported module accepted')
    states = json.loads((batch / 'state.json').read_text())
    assert len(states) == 8 and all(state['returncode'] == 0 for state in states)
    analysis = json.loads((batch / 'analysis.json').read_text())
    result = {}
    for condition in ('zero', 'declared'):
        root = RUNS / f'{batch.name}-{condition}-843-1'
        weighted = scores(root / 'initial-ir-scores.tsv')
        assert len(weighted) == 120
        owners = {owner for owner, module in weighted}
        assert len(owners) == 20 and all(sum(entity == owner for entity, module in weighted) == 6 for owner in owners)
        expected = {pair: value / factor(pair) for pair, value in weighted.items()}
        rows = (batch / f'{condition}-path-decomposition.tsv').read_text().splitlines()[1:]
        assert len(rows) == len(expected)
        for row in rows:
            owner, module, value, multiplier, without = row.split('\t')
            assert float(value) == weighted[owner, module]
            assert float(multiplier) == factor((owner, module))
            assert math.isclose(float(without), expected[owner, module], rel_tol=1e-14)
        exception = 'net.sf.jabref.JabRefException'
        result[condition] = {'exception_model_score': weighted[exception, 'model'],
                             'exception_weighted_top': top(weighted, exception),
                             'path_top_changes': len(analysis[condition]['post_path_top_changes'])}
    output = {'checks': 'eight runs, full Cartesian IR output, exact decomposition, five factor controls',
              'scope': 'deterministic recheck, not independent scientific review',
              'checker_sha256': digest(Path(__file__)), 'results': result}
    (batch / 'validation.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
