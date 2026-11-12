"""Independently check snapshot query counts and inspect exploratory candidate ranks."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from check_inmap_factorial_trace import read_counts
from run_inmap_snapshots import ROOT, RUNS, WORDS, digest, scores


def main():
    batch = RUNS / sys.argv[1]
    manifest = json.loads((batch / 'manifest.json').read_text())
    assert digest(batch / 'manifest.json') == (batch / 'manifest.sha256').read_text().strip()
    for name, checksum in manifest['sha256'].items():
        candidates = [ROOT / name]
        archived_name = 'runner.py' if name.endswith('/run_inmap_input_probe.py') else Path(name).name
        candidates.append(RUNS / f'{batch.name}-empty-zero-1' / archived_name)
        assert any(path.exists() and digest(path) == checksum for path in candidates), name
    words = {}
    for row in WORDS.read_text().splitlines():
        owner, methods = row.split('\t')
        words[owner] = set(methods.split(',')) if methods else set()
    states = json.loads((batch / 'state.json').read_text())
    assert len(states) == 12 and all(state['returncode'] == 0 for state in states)
    for state in states:
        directory = RUNS / state['run']
        report = json.loads((directory / 'report.json').read_text())
        for name, checksum in report['artifact_sha256'].items():
            assert digest(directory / name) == checksum
        accepted = defaultdict(set)
        for row in (directory / 'snapshot-input.tsv').read_text().splitlines():
            module, owner = row.split('\t')
            accepted[module].add(owner)
        seen = set()
        for row in (directory / 'trace-queries.tsv').read_text().splitlines():
            page, module, size, budget, counts, raw, parsed = row.split('\t')
            assert page == '1' and module not in seen
            seen.add(module)
            assert int(size) == len(accepted[module]) and int(budget) >= 0
            expected = Counter()
            if '-declared-' in state['run']:
                for owner in accepted[module]:
                    expected.update(words[owner])
            assert read_counts(counts) == dict(expected)
        assert len(seen) == 6
        accepted_owners = set().union(*accepted.values())
        assert not accepted_owners.intersection(owner for owner, module in scores(directory / 'initial-ir-scores.tsv'))
    analyses = {}
    for label in ('empty', 'first', 'last'):
        for condition in ('zero', 'declared'):
            for name in ('initial-ir-scores.tsv', 'trace-queries.tsv', 'filtered-classes.txt', 'snapshot-input.tsv'):
                first = RUNS / f'{batch.name}-{label}-{condition}-1' / name
                second = RUNS / f'{batch.name}-{label}-{condition}-2' / name
                assert first.read_bytes() == second.read_bytes()
        zero = RUNS / f'{batch.name}-{label}-zero-1'
        declared = RUNS / f'{batch.name}-{label}-declared-1'
        assert (zero / 'snapshot-input.tsv').read_bytes() == (declared / 'snapshot-input.tsv').read_bytes()
        before, after = scores(zero / 'initial-ir-scores.tsv'), scores(declared / 'initial-ir-scores.tsv')
        queries_before = {row.split('\t')[1]: row.split('\t')[5:] for row in (zero / 'trace-queries.tsv').read_text().splitlines()}
        queries_after = {row.split('\t')[1]: row.split('\t')[5:] for row in (declared / 'trace-queries.tsv').read_text().splitlines()}
        analyses[label] = {'accepted_count': len((zero / 'snapshot-input.tsv').read_text().splitlines()),
                           'changed_queries': sum(queries_before[key] != queries_after[key] for key in queries_before),
                           'before_pairs': len(before), 'after_pairs': len(after),
                           'changed_common_scores': sum(before[key] != after[key] for key in before.keys() & after.keys()),
                           'added_pairs': sorted(after.keys() - before.keys()), 'removed_pairs': sorted(before.keys() - after.keys())}
        if label == 'empty':
            assert before == after and queries_before == queries_after
            assert not (zero / 'trace-accepted.tsv').exists() and not (declared / 'trace-accepted.tsv').exists()
        rows = ['owner\tmodule\tbefore\tafter']
        for pair in sorted(before.keys() | after.keys()):
            if before.get(pair) != after.get(pair):
                rows.append('\t'.join(pair) + '\t' + str(before.get(pair, 'missing')) + '\t' + str(after.get(pair, 'missing')))
        (batch / (label + '-score-deltas.tsv')).write_text('\n'.join(rows) + '\n')
    (batch / 'analysis.json').write_text(json.dumps(analyses, indent=2) + '\n')
    baseline = RUNS / '2026-11-12-inmap-factorial-02-u0-1'
    variant = RUNS / '2026-11-12-inmap-factorial-02-ud-1'
    pairs = lambda path: {tuple(row.split('\t')) for row in path.read_text().splitlines()}
    additions = pairs(variant / 'acceptedMappings.tsv') - pairs(baseline / 'acceptedMappings.tsv')
    targets = sorted(additions | {('net.sf.jabref.JabRefException', 'model')})
    observations = []
    for label in ('first', 'last'):
        for condition in ('zero', 'declared'):
            values = scores(RUNS / f'{batch.name}-{label}-{condition}-1/initial-ir-scores.tsv')
            for owner, oracle in targets:
                candidates = {module: score for (entity, module), score in values.items() if entity == owner}
                best = max(candidates.values()) if candidates else None
                observations.append({'snapshot': label, 'condition': condition, 'owner': owner,
                                     'oracle': oracle, 'scores': candidates,
                                     'top_modules': sorted(module for module, score in candidates.items() if score == best)})
    output = {'checks': 'all 12 query counts recomputed; accepted classes excluded; frozen hashes valid',
              'analyzer_sha256': digest(Path(__file__)),
              'scope': 'candidate ranks are exploratory, selected from prior factorial outcomes; no selector/rejection/threshold simulation',
              'targets': len(targets), 'observations': observations}
    (batch / 'validation-and-candidates.json').write_text(json.dumps(output, indent=2) + '\n')
    print(output['checks'])


if __name__ == '__main__':
    main()
