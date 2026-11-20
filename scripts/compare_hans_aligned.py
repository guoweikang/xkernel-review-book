"""Align historical predictions to the frozen modern-model development sample."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid ID')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol = ROOT / 'research/protocols/hans-aligned-comparison-v1.json'
    plan = json.loads(protocol.read_text())
    modern, historical = ROOT / plan['modern_run'], ROOT / plan['historical_run']
    for folder in (modern, historical):
        for relative, digest in json.loads((folder / 'report.json').read_text())['artifact_sha256'].items():
            if sha(folder / relative) != digest:
                raise ValueError('parent hash mismatch')
    data = ROOT / plan['data']
    modern_manifest = json.loads((modern / 'manifest.json').read_text())
    if sha(data) != modern_manifest['input_sha256'][plan['data']]:
        raise ValueError('reference changed')
    with data.open() as stream:
        reference_rows = list(csv.DictReader(stream, delimiter='\t'))
    reference = {row['pairID']: row for row in reference_rows}
    if len(reference) != len(reference_rows):
        raise ValueError('duplicate reference')
    identities = json.loads((modern / 'selected-ids.json').read_text())
    if len(identities) != 300 or len(set(identities)) != 300 or set(identities) - reference.keys():
        raise ValueError('invalid sample')
    predictions = {}
    current = [json.loads(line) for line in (modern / 'predictions-1.jsonl').read_text().splitlines()]
    if [row['pairID'] for row in current] != identities:
        raise ValueError('modern coverage differs')
    predictions['modern'] = {row['pairID']: row['binary_label'] for row in current}
    for filename in plan['historical_files']:
        with (historical / filename).open() as stream:
            rows = list(csv.DictReader(stream))
        indexed = {row['pairID']: row['gold_label'] for row in rows}
        if len(indexed) != len(rows) or set(indexed) != set(reference):
            raise ValueError('historical coverage differs')
        predictions[filename] = {identity: indexed[identity] for identity in identities}
    if any(label not in ('entailment', 'non-entailment') for mapping in predictions.values() for label in mapping.values()):
        raise ValueError('invalid label')
    summaries = {}
    for method, mapping in predictions.items():
        groups = defaultdict(lambda: [0, 0])
        for identity in identities:
            row = reference[identity]
            hit = int(mapping[identity] == row['gold_label'])
            for key in ['overall', 'gold:' + row['gold_label'], 'subcase:' + row['subcase']]:
                groups[key][0] += hit
                groups[key][1] += 1
        summaries[method] = {key: {'correct': hits, 'total': total, 'accuracy': hits / total} for key, (hits, total) in groups.items()}
    discordances = {}
    for method in plan['historical_files']:
        partitions = {name: [] for name in ('both_correct', 'both_wrong', 'modern_only', 'historical_only')}
        for identity in identities:
            gold = reference[identity]['gold_label']
            current_hit = predictions['modern'][identity] == gold
            old_hit = predictions[method][identity] == gold
            key = 'both_correct' if current_hit and old_hit else 'both_wrong' if not current_hit and not old_hit else 'modern_only' if current_hit else 'historical_only'
            partitions[key].append(identity)
        if sum(map(len, partitions.values())) != 300:
            raise ValueError('partition incomplete')
        if len(partitions['both_correct']) + len(partitions['modern_only']) != summaries['modern']['overall']['correct']:
            raise ValueError('modern count inconsistent')
        if len(partitions['both_correct']) + len(partitions['historical_only']) != summaries[method]['overall']['correct']:
            raise ValueError('historical count inconsistent')
        discordances[method] = partitions
    errors = defaultdict(list)
    for identity in sorted(identities):
        row = reference[identity]
        if predictions['modern'][identity] != row['gold_label']:
            errors[row['subcase']].append(identity)
    review = [{'subcase': subcase, 'pairID': values[0], 'all_error_ids': values} for subcase, values in sorted(errors.items())]
    shutil.copy2(protocol, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    (output / 'aligned-predictions.json').write_text(json.dumps(predictions, indent=2) + '\n')
    (output / 'discordances.json').write_text(json.dumps(discordances, indent=2) + '\n')
    (output / 'review-queue.json').write_text(json.dumps(review, indent=2) + '\n')
    (output / 'manifest.json').write_text(json.dumps({str(path.relative_to(ROOT)): sha(path) for path in [data, protocol, modern / 'report.json', historical / 'report.json']}, indent=2) + '\n')
    report = {'scope': plan['scope'], 'metrics': summaries,
              'discordance_counts': {method: {key: len(values) for key, values in partition.items()} for method, partition in discordances.items()},
              'error_subcases': len(review), 'inference_runs': 0,
              'artifact_sha256': {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'overall': {method: result['overall'] for method, result in summaries.items()}, 'discordances': report['discordance_counts'], 'error_subcases': len(review)}, indent=2))
    for item in review:
        row = reference[item['pairID']]
        print(item['subcase'], item['pairID'], row['gold_label'], row['sentence1'], '=>', row['sentence2'])


if __name__ == '__main__':
    main()
