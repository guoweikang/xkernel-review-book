"""Freeze and run paired IR probes at preselected O0 feedback snapshots."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
BASE = RUNS / '2026-11-12-inmap-factorial-02-o0-1'
WORDS = RUNS / '2026-11-12-inmap-factorial-02/declared-method-input.tsv'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scores(path):
    result = {}
    for row in path.read_text().splitlines():
        owner, module, value = row.split('\t')
        assert (owner, module) not in result
        result[owner, module] = float(value)
    return result


def main():
    batch_id = sys.argv[1]
    assert batch_id and all(character.isalnum() or character in '-_' for character in batch_id)
    batch = RUNS / batch_id
    batch.mkdir()
    snapshots = {}
    for row in (BASE / 'trace-accepted.tsv').read_text().splitlines():
        page, module, owner = row.split('\t')
        snapshots.setdefault(int(page), []).append(module + '\t' + owner)
    selected = {'empty': [], 'first': snapshots[min(snapshots)], 'last': snapshots[max(snapshots)]}
    for label, rows in selected.items():
        (batch / (label + '.tsv')).write_text(''.join(row + '\n' for row in sorted(rows)))
    frozen = [BASE / 'trace-accepted.tsv', WORDS, Path(__file__),
              ROOT / 'scripts/run_inmap_input_probe.py', ROOT / 'research/tools/InMapSnapshotProbe.java',
              ROOT / 'research/tools/InMapTrace.java'] + list(batch.glob('*.tsv'))
    manifest = {'question': 'same accepted snapshot: effect of declared-method query feedback on IR scores',
                'selection': {'first': min(snapshots), 'last': max(snapshots)},
                'scope': 'development-data mechanism probe, not paper reproduction or independent accuracy',
                'limits': {'runs': 12, 'wrapper_seconds': 240, 'inner_seconds': 180},
                'checks': ['empty control identical', 'two repeats byte-identical', 'paired accepted snapshots identical',
                           'six queries each', 'all artifacts match report hashes'],
                'metrics': ['query changes', 'common score changes', 'added and removed score pairs'],
                'sha256': {str(path.relative_to(ROOT)): digest(path) for path in frozen}}
    (batch / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (batch / 'manifest.sha256').write_text(digest(batch / 'manifest.json') + '\n')
    states = []
    for label in selected:
        for repeat in (1, 2):
            for condition in ('zero', 'declared'):
                run_id = f'{batch_id}-{label}-{condition}-{repeat}'
                command = [sys.executable, 'scripts/run_inmap_input_probe.py', '--run-id', run_id,
                           '--snapshot-input', str(batch / (label + '.tsv'))]
                if condition == 'declared':
                    command += ['--declared-method-input', str(WORDS)]
                for name, checksum in manifest['sha256'].items():
                    assert digest(ROOT / name) == checksum
                try:
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=240)
                    code, stdout, stderr = result.returncode, result.stdout, result.stderr
                except subprocess.TimeoutExpired as error:
                    code, stdout, stderr = 124, error.stdout or b'', error.stderr or b''
                (batch / (run_id + '.stdout')).write_bytes(stdout)
                (batch / (run_id + '.stderr')).write_bytes(stderr)
                states.append({'run': run_id, 'returncode': code})
                (batch / 'state.json').write_text(json.dumps(states, indent=2) + '\n')
                print(run_id, code, flush=True)
    assert all(state['returncode'] == 0 for state in states), 'failed runs preserved; no analysis'
    analyses = {}
    core = ('initial-ir-scores.tsv', 'trace-queries.tsv', 'trace-accepted.tsv', 'filtered-classes.txt')
    for state in states:
        directory = RUNS / state['run']
        report = json.loads((directory / 'report.json').read_text())
        for name, checksum in report['artifact_sha256'].items():
            assert digest(directory / name) == checksum
        assert len((directory / 'trace-queries.tsv').read_text().splitlines()) == 6
    for label in selected:
        for condition in ('zero', 'declared'):
            for name in core:
                first = RUNS / f'{batch_id}-{label}-{condition}-1' / name
                second = RUNS / f'{batch_id}-{label}-{condition}-2' / name
                assert first.read_bytes() == second.read_bytes(), (label, condition, name)
        zero = RUNS / f'{batch_id}-{label}-zero-1'
        declared = RUNS / f'{batch_id}-{label}-declared-1'
        assert (zero / 'trace-accepted.tsv').read_bytes() == (declared / 'trace-accepted.tsv').read_bytes()
        before, after = scores(zero / 'initial-ir-scores.tsv'), scores(declared / 'initial-ir-scores.tsv')
        common = before.keys() & after.keys()
        changed = [pair for pair in common if before[pair] != after[pair]]
        queries_before = {row.split('\t')[1]: row.split('\t')[5:] for row in (zero / 'trace-queries.tsv').read_text().splitlines()}
        queries_after = {row.split('\t')[1]: row.split('\t')[5:] for row in (declared / 'trace-queries.tsv').read_text().splitlines()}
        analyses[label] = {'accepted_count': len(selected[label]), 'changed_queries': sum(queries_before[key] != queries_after[key] for key in queries_before),
                           'before_pairs': len(before), 'after_pairs': len(after), 'changed_common_scores': len(changed),
                           'added_pairs': len(after.keys() - before.keys()), 'removed_pairs': len(before.keys() - after.keys())}
        rows = ['owner\tmodule\tbefore\tafter']
        for pair in sorted(before.keys() | after.keys()):
            if before.get(pair) != after.get(pair):
                rows.append('\t'.join(pair) + '\t' + str(before.get(pair, 'missing')) + '\t' + str(after.get(pair, 'missing')))
        (batch / (label + '-score-deltas.tsv')).write_text('\n'.join(rows) + '\n')
        if label == 'empty':
            assert before == after and queries_before == queries_after
    (batch / 'analysis.json').write_text(json.dumps(analyses, indent=2) + '\n')
    print(json.dumps(analyses, indent=2))


if __name__ == '__main__':
    main()
