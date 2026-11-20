"""Fetch pinned author predictions and replay their unmodified evaluator."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

from run_hans_evaluator import ROOT, sha, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run id')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    originals = ROOT / 'research/evidence/originals' / args.run_id
    folder.mkdir()
    originals.mkdir()
    protocol = ROOT / 'research/protocols/hans-prediction-replay-v1.json'
    plan = json.loads(protocol.read_text())
    data, evaluator = ROOT / plan['data'], ROOT / plan['evaluator']
    previous = json.loads((ROOT / 'research/evidence/runs/2026-11-13-hans-evaluator-01/manifest.json').read_text())
    for path in (data, evaluator):
        if sha(path) != previous['inputs'][str(path.relative_to(ROOT))]:
            raise ValueError('baseline identity changed')
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    shutil.copy2(ROOT / 'scripts/run_hans_evaluator.py', folder / 'validator-source.py')
    with data.open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    identities = {row['pairID'] for row in rows}
    manifest = {'revision': plan['revision'], 'inputs': {str(path.relative_to(ROOT)): sha(path) for path in (data, evaluator, protocol)}, 'downloads': []}
    results = {}
    for filename in plan['files']:
        url = f'https://raw.githubusercontent.com/tommccoy1/hans/{plan["revision"]}/{filename}'
        with urllib.request.urlopen(url, timeout=90) as response:
            raw = response.read()
        original = originals / filename
        original.write_bytes(raw)
        manifest['downloads'].append({'url': url, 'path': str(original.relative_to(ROOT)), 'sha256': sha(original), 'bytes': len(raw)})
        (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        with original.open() as stream:
            source = list(csv.DictReader(stream))
        raw_labels = Counter(row['gold_label'] for row in source)
        if set(raw_labels) - {'entailment', 'non-entailment', 'neutral', 'contradiction'}:
            raise ValueError('unexpected author label')
        predictions = [(row['pairID'], 'entailment' if row['gold_label'] == 'entailment' else 'non-entailment') for row in source]
        validate(predictions, identities)
        predicted = dict(predictions)
        normalized = folder / (filename + '.csv')
        with normalized.open('w') as stream:
            writer = csv.writer(stream)
            writer.writerow(['pairID', 'gold_label'])
            writer.writerows(predictions)
        groups = defaultdict(lambda: [0, 0])
        correct = 0
        for row in rows:
            hit = int(row['gold_label'] == predicted[row['pairID']])
            correct += hit
            section = 'Heuristic entailed results:' if row['gold_label'] == 'entailment' else 'Heuristic non-entailed results:'
            for group in [(section, row['heuristic']), ('Subcase results:', row['subcase']), ('Template results:', row['template'])]:
                groups[group][0] += hit
                groups[group][1] += 1
        expected = {key: hits / total for key, (hits, total) in groups.items()}
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'heuristics_evaluation_set.txt').symlink_to(data)
            for repeat in range(1, plan['repeats'] + 1):
                process = subprocess.run([sys.executable, str(evaluator), str(normalized)], cwd=temporary, capture_output=True, text=True, timeout=60)
                stdout = folder / f'{filename}-{repeat}.stdout.txt'
                stdout.write_text(process.stdout)
                (folder / f'{filename}-{repeat}.stderr.txt').write_text(process.stderr)
                if process.returncode:
                    raise ValueError('author evaluation failed')
                observed = {}
                section = None
                for line in process.stdout.splitlines():
                    if line.endswith('results:'):
                        section = line
                    elif line.strip():
                        key, value = line.rsplit(': ', 1)
                        observed[(section, key)] = float(value)
                if observed != expected:
                    raise ValueError('independent count mismatch')
                if repeat > 1 and stdout.read_bytes() != (folder / f'{filename}-1.stdout.txt').read_bytes():
                    raise ValueError('repeat mismatch')
        results[filename] = {'correct': correct, 'total': len(rows), 'accuracy': correct / len(rows),
                             'raw_labels': dict(raw_labels), 'groups_checked': len(groups),
                             'groups': [{'section': section, 'group': group, 'correct': hits, 'total': total, 'accuracy': hits / total}
                                        for (section, group), (hits, total) in groups.items()]}
    report = {'scope': plan['scope'], 'results': results, 'author_evaluator_runs': 8, 'model_inference_runs': 0,
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: {key: value for key, value in result.items() if key != 'groups'} for name, result in results.items()}, indent=2))


if __name__ == '__main__':
    main()
