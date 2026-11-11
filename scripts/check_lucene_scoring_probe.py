"""Check recorded component observations; not a semantic accuracy evaluation."""

import argparse
import hashlib
import json
from pathlib import Path


def check(run):
    report = json.loads((run / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected, name
    assert json.loads((run / 'execution.json').read_text())['returncode'] == 0
    rows = [line.split('\t') for line in (run / 'stdout.txt').read_text().splitlines()]
    queries = {(row[1], row[2]): row[3:] for row in rows if row[0] == 'QUERY'}
    hits = {}
    for row in rows:
        if row[0] == 'HIT':
            hits.setdefault((row[1], row[2]), {})[row[3]] = (float(row[4]), float(row[5]))
    template = '( cpu*~ )^30.0 ( node*~ )^2.0'
    for mode in ('default', 'classic-control'):
        assert queries[(mode, 'cpu*~')] == ['PrefixQuery', 'contents:cpu*']
        assert queries[(mode, 'cpu~')][0] == 'FuzzyQuery'
        prefix = hits[(mode, 'cpu*~')]
        assert prefix == hits[(mode, 'cpu*')]
        assert 'driver.Typo' not in prefix
        assert 'driver.Typo' in hits[(mode, 'cpu~')]
        assert {scores[0] for scores in prefix.values()} == {1.0}
        assert hits[(mode, template)]['driver.Typo'][0] == 2.0
        assert hits[(mode, template)]['driver.Repeated'][0] == 32.0
        assert hits[(mode, 'cpu')]['driver.Repeated'][0] > hits[(mode, 'cpu')]['cpu.Node'][0]
        for query in ('cpu', 'cpu*', 'cpu~', 'cpu*~', template):
            first = hits[(mode, query)]['driver.Node']
            second = hits[(mode, query)]['cpu.Node']
            assert first[0] == second[0]
            assert abs(second[1] / first[1] - 900.0) < 0.001
    assert hits[('default', template)] == hits[('classic-control', template)]
    assert hits[('default', 'cpu')] != hits[('classic-control', 'cpu')]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--repeat', type=Path)
    args = parser.parse_args()
    original = check(args.run)
    if args.repeat:
        repeated = check(args.repeat)
        for name in ('stdout.txt', 'dependencies.json', 'LuceneScoringProbe.java'):
            assert original['artifact_sha256'][name] == repeated['artifact_sha256'][name]
    print('PASS: artifact hashes, parsing, typo/prefix controls, score controls, path boost; repeat if supplied')


if __name__ == '__main__':
    main()
