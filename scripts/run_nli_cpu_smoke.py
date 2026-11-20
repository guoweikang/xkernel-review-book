"""Run the frozen local-only NLI development smoke experiment."""

import argparse
from collections import defaultdict
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import signal
import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timeout_handler(signum, frame):
    raise TimeoutError('frozen 30-minute inference budget exceeded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (character.isalnum() or character in '-_') for character in args.run_id):
        raise ValueError('invalid run id')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(1800)
    started = time.monotonic()
    protocol = ROOT / 'research/protocols/nli-cpu-smoke-v1.json'
    plan = json.loads(protocol.read_text())
    model_path = ROOT / 'research/evidence/originals/2026-11-13-nli-weights-01'
    downloads = ROOT / 'research/evidence/runs/2026-11-13-nli-weights-01/downloads.json'
    assets = json.loads(downloads.read_text())
    if {path.name for path in model_path.iterdir()} != {record['name'] for record in assets}:
        raise ValueError('unregistered model asset')
    for record in assets:
        if record['url'] != f'https://huggingface.co/{plan["model"]}/resolve/{plan["revision"]}/{record["name"]}':
            raise ValueError('wrong asset revision')
        if sha(model_path / record['name']) != record['sha256']:
            raise ValueError('model asset hash mismatch')
    if sha(model_path / 'model.safetensors') != plan['weight_sha256']:
        raise ValueError('unexpected weight')
    data = ROOT / plan['data']
    sources = json.loads((ROOT / 'research/evidence/runs/2026-11-13-relation-benchmarks-01/sources.json').read_text())
    if sha(data) != next(row['sha256'] for row in sources if row['name'] == 'hans-data.tsv'):
        raise ValueError('data changed')
    groups = defaultdict(list)
    with data.open() as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            groups[row['subcase']].append(row)
    selected = [row for group in sorted(groups) for row in sorted(groups[group], key=lambda row: row['pairID'])[:10]]
    if len(selected) != 300 or len({row['pairID'] for row in selected}) != 300 or len(groups) != 30:
        raise ValueError('selection differs')
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    shutil.copy2(downloads, folder / 'model-downloads.json')
    (folder / 'selected-ids.json').write_text(json.dumps([row['pairID'] for row in selected], indent=2) + '\n')
    manifest = {'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in (data, protocol, downloads, Path(__file__))},
                'packages': {distribution.metadata['Name']: distribution.version for distribution in importlib.metadata.distributions()},
                'threads': 4, 'device': 'cpu', 'dtype': 'float32'}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True, trust_remote_code=False, use_safetensors=True)
    model = model.to(device='cpu', dtype=torch.float32).eval()
    expected = {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
    if model.config.id2label != expected:
        raise ValueError('unexpected label mapping')
    lengths = [len(tokenizer(row['sentence1'], row['sentence2'], truncation=False)['input_ids']) for row in selected]
    (folder / 'lengths.json').write_text(json.dumps(lengths) + '\n')
    runs = []
    for repeat in (1, 2):
        predictions = []
        with (folder / f'predictions-{repeat}.jsonl').open('w') as stream, torch.inference_mode():
            for start in range(0, len(selected), 8):
                batch = selected[start:start + 8]
                features = tokenizer([row['sentence1'] for row in batch], [row['sentence2'] for row in batch],
                                     padding=True, truncation=True, max_length=128, return_tensors='pt')
                logits = model(**features).logits
                if tuple(logits.shape) != (len(batch), 3):
                    raise ValueError('unexpected logit shape')
                if not torch.isfinite(logits).all():
                    raise ValueError('nonfinite logits')
                for row, scores in zip(batch, logits.tolist()):
                    label = expected[max(range(3), key=lambda index: scores[index])]
                    result = {'pairID': row['pairID'], 'logits': scores, 'label': label,
                              'binary_label': 'entailment' if label == 'entailment' else 'non-entailment'}
                    predictions.append(result)
                    stream.write(json.dumps(result) + '\n')
                stream.flush()
        if [row['pairID'] for row in predictions] != [row['pairID'] for row in selected]:
            raise ValueError('incomplete or misordered predictions')
        runs.append(predictions)
    counts = defaultdict(lambda: [0, 0])
    for row, prediction in zip(selected, runs[0]):
        hit = int(row['gold_label'] == prediction['binary_label'])
        for group in ['overall', 'gold:' + row['gold_label'], 'subcase:' + row['subcase']]:
            counts[group][0] += hit
            counts[group][1] += 1
    report = {'scope': plan['purpose'], 'examples': len(selected), 'passes': 2,
              'truncated_examples': sum(length > 128 for length in lengths), 'max_input_length': max(lengths),
              'prediction_agreement': sum(left['label'] == right['label'] for left, right in zip(*runs)) / len(selected),
              'max_logit_difference': max(abs(left - right) for first, second in zip(*runs) for left, right in zip(first['logits'], second['logits'])),
              'metrics': {group: {'correct': hits, 'total': total, 'accuracy': hits / total} for group, (hits, total) in counts.items()},
              'elapsed_seconds': time.monotonic() - started,
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps({key: value for key, value in report.items() if key not in ('metrics', 'artifact_sha256')}, indent=2))
    print(json.dumps(report['metrics']['overall']))


if __name__ == '__main__':
    main()
