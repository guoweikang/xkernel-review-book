"""Validate the pinned HANS evaluator with deterministic prediction controls."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(predictions, identities):
    if len(predictions) != len(identities) or {identity for identity, label in predictions} != identities:
        raise ValueError('missing, extra or duplicate IDs')
    if any(label not in ('entailment', 'non-entailment') for identity, label in predictions):
        raise ValueError('invalid binary label')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run id')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol = ROOT / 'research/protocols/hans-evaluator-v1.json'
    plan = json.loads(protocol.read_text())
    data, evaluator = ROOT / plan['data'], ROOT / plan['evaluator']
    sources = json.loads((ROOT / 'research/evidence/runs/2026-11-13-relation-benchmarks-01/sources.json').read_text())
    if sha(data) != next(source['sha256'] for source in sources if source['name'] == 'hans-data.tsv'):
        raise ValueError('wrong data snapshot')
    with data.open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    identities = {row['pairID'] for row in rows}
    if len(identities) != len(rows):
        raise ValueError('duplicate reference IDs')
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    manifest = {'revision': plan['revision'], 'evaluator_url': f'https://raw.githubusercontent.com/tommccoy1/hans/{plan["revision"]}/evaluate_heur_output.py',
                'inputs': {str(path.relative_to(ROOT)): sha(path) for path in (protocol, data, evaluator, Path(__file__))}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    summaries = {}
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        (workspace / 'heuristics_evaluation_set.txt').symlink_to(data)
        for condition in plan['conditions']:
            predictions = []
            for row in rows:
                if condition == 'token_subset':
                    premise = set(re.findall('[a-z]+', row['sentence1'].lower()))
                    hypothesis = set(re.findall('[a-z]+', row['sentence2'].lower()))
                    label = 'entailment' if hypothesis <= premise else 'non-entailment'
                elif condition == 'gold_plumbing_only':
                    label = row['gold_label']
                elif condition == 'inverted_gold_plumbing_only':
                    label = 'non-entailment' if row['gold_label'] == 'entailment' else 'entailment'
                else:
                    label = 'entailment' if condition == 'always_entailment' else 'non-entailment'
                predictions.append((row['pairID'], label))
            validate(predictions, identities)
            prediction_path = folder / f'{condition}.csv'
            with prediction_path.open('w') as stream:
                writer = csv.writer(stream)
                writer.writerow(['pairID', 'gold_label'])
                writer.writerows(predictions)
            counts = defaultdict(lambda: [0, 0])
            correct = 0
            for row, (identity, label) in zip(rows, predictions):
                hit = int(label == row['gold_label'])
                correct += hit
                section = 'Heuristic entailed results:' if row['gold_label'] == 'entailment' else 'Heuristic non-entailed results:'
                for group in [(section, row['heuristic']), ('Subcase results:', row['subcase']), ('Template results:', row['template'])]:
                    counts[group][0] += hit
                    counts[group][1] += 1
            expected = {key: hits / total for key, (hits, total) in counts.items()}
            for repeat in range(1, plan['repeats'] + 1):
                execution = subprocess.run([sys.executable, str(evaluator), str(prediction_path)], cwd=workspace,
                                           capture_output=True, text=True, timeout=60)
                stdout = folder / f'{condition}-{repeat}.stdout.txt'
                stdout.write_text(execution.stdout)
                (folder / f'{condition}-{repeat}.stderr.txt').write_text(execution.stderr)
                if execution.returncode:
                    raise ValueError('author evaluator failed; see stderr')
                observed = {}
                section = None
                for line in execution.stdout.splitlines():
                    if line.endswith('results:'):
                        section = line
                    elif line.strip():
                        group, value = line.rsplit(': ', 1)
                        observed[(section, group)] = float(value)
                if observed != expected:
                    raise ValueError('group counts differ')
                if repeat > 1 and stdout.read_bytes() != (folder / f'{condition}-1.stdout.txt').read_bytes():
                    raise ValueError('non-deterministic evaluator')
            summaries[condition] = {'correct': correct, 'total': len(rows), 'accuracy': correct / len(rows),
                                    'groups_checked': len(expected), 'predicted_entailment': sum(label == 'entailment' for identity, label in predictions)}
        rejected = []
        for name, altered in [('missing', predictions[:-1]), ('duplicate', predictions[:-1] + [predictions[0]]),
                              ('invalid_label', [(predictions[0][0], 'typo')] + predictions[1:])]:
            try:
                validate(altered, identities)
            except ValueError:
                rejected.append(name)
            else:
                raise AssertionError(name)
    report = {'scope': plan['scope'], 'summaries': summaries, 'rejected_controls': rejected,
              'author_executions': 10, 'trained_model_executions': 0,
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
