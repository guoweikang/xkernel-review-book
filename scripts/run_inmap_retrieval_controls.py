"""Paired retrieval-cap experiment and post-retrieval path-factor decomposition."""

import json
import math
from pathlib import Path
import subprocess
import sys

from run_inmap_snapshots import ROOT, RUNS, WORDS, digest, scores


def top(values, owner):
    candidates = {module: score for (entity, module), score in values.items() if entity == owner}
    maximum = max(candidates.values()) if candidates else None
    return sorted(module for module, score in candidates.items() if score == maximum)


def factor(pair):
    owner, module = pair
    assert module in {'model', 'logic', 'pref', 'gui ui', 'cli', 'global'}
    return 33.0 if any(word in owner for word in module.split()) else 1.0 / 33.0


def main():
    batch_id = sys.argv[1]
    assert batch_id and all(character.isalnum() or character in '-_' for character in batch_id)
    batch = RUNS / batch_id
    batch.mkdir()
    snapshot = RUNS / '2026-11-12-inmap-snapshots-01/last.tsv'
    frozen = [snapshot, WORDS, Path(__file__), ROOT / 'scripts/run_inmap_input_probe.py',
              ROOT / 'research/tools/InMapSnapshotProbe.java', ROOT / 'research/tools/InMapTrace.java']
    manifest = {'question': 'is missing model score retrieval truncation; does post-retrieval path weighting change top modules?',
                'design': 'fixed O0 last snapshot; caps 842/843 x method tables zero/D x two repeats',
                'limits': {'runs': 8, 'wall_seconds_per_run': 240, 'inner_seconds': 180},
                'metrics': ['added pairs', 'common scores invariant across caps', 'query invariance across caps',
                            'top-module changes after inverse post-retrieval factor'],
                'limitations': 'postprocessing is not removing query module-name boost, nor full-loop ablation; development data',
                'sha256': {str(path.relative_to(ROOT)): digest(path) for path in frozen}}
    (batch / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (batch / 'manifest.sha256').write_text(digest(batch / 'manifest.json') + '\n')
    states = []
    for repeat in (1, 2):
        for condition in ('zero', 'declared'):
            for cap in (842, 843):
                run_id = f'{batch_id}-{condition}-{cap}-{repeat}'
                command = [sys.executable, 'scripts/run_inmap_input_probe.py', '--run-id', run_id,
                           '--snapshot-input', str(snapshot), '--retrieval-limit', str(cap)]
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
    assert all(state['returncode'] == 0 for state in states)
    analyses = {}
    for condition in ('zero', 'declared'):
        for cap in (842, 843):
            for artifact in ('initial-ir-scores.tsv', 'trace-queries.tsv', 'snapshot-input.tsv', 'filtered-classes.txt'):
                assert (RUNS / f'{batch_id}-{condition}-{cap}-1' / artifact).read_bytes() == (RUNS / f'{batch_id}-{condition}-{cap}-2' / artifact).read_bytes()
        low = RUNS / f'{batch_id}-{condition}-842-1'
        high = RUNS / f'{batch_id}-{condition}-843-1'
        assert (low / 'trace-queries.tsv').read_bytes() == (high / 'trace-queries.tsv').read_bytes()
        old = RUNS / f'2026-11-12-inmap-snapshots-01-last-{condition}-1'
        assert (old / 'initial-ir-scores.tsv').read_bytes() == (low / 'initial-ir-scores.tsv').read_bytes()
        before, after = scores(low / 'initial-ir-scores.tsv'), scores(high / 'initial-ir-scores.tsv')
        assert before.keys() <= after.keys() and all(before[pair] == after[pair] for pair in before)
        unweighted = {pair: value / factor(pair) for pair, value in after.items()}
        assert all(math.isclose(unweighted[pair] * factor(pair), value, rel_tol=1e-14) for pair, value in after.items())
        owners = sorted({owner for owner, module in after})
        changes = [{'owner': owner, 'weighted_top': top(after, owner), 'without_post_path_top': top(unweighted, owner)}
                   for owner in owners if top(after, owner) != top(unweighted, owner)]
        analyses[condition] = {'pairs_842': len(before), 'pairs_843': len(after),
                               'added': [{'owner': owner, 'module': module, 'score': after[owner, module]} for owner, module in sorted(after.keys() - before.keys())],
                               'post_path_top_changes': changes, 'owners_in_ir_output': len(owners)}
        rows = ['owner\tmodule\tweighted\tpost_path_factor\twithout_post_path_factor']
        rows += ['\t'.join(pair) + f'\t{after[pair]}\t{factor(pair)}\t{unweighted[pair]}' for pair in sorted(after)]
        (batch / f'{condition}-path-decomposition.tsv').write_text('\n'.join(rows) + '\n')
    for state in states:
        directory = RUNS / state['run']
        report = json.loads((directory / 'report.json').read_text())
        assert report['returncode'] == 0
        for name, checksum in report['artifact_sha256'].items():
            assert digest(directory / name) == checksum
    (batch / 'analysis.json').write_text(json.dumps(analyses, indent=2) + '\n')
    print(json.dumps(analyses, indent=2))


if __name__ == '__main__':
    main()
