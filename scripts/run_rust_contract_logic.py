"""Generate finite-world reference labels before any local NLI inference."""

import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(formula, world):
    if isinstance(formula, str):
        return world[formula]
    operation, *arguments = formula
    if operation == 'not' and len(arguments) == 1:
        return not evaluate(arguments[0], world)
    if operation == 'and' and len(arguments) == 2:
        return evaluate(arguments[0], world) and evaluate(arguments[1], world)
    if operation == 'implies' and len(arguments) == 2:
        return not evaluate(arguments[0], world) or evaluate(arguments[1], world)
    raise ValueError('invalid formula')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(not (character.isalnum() or character in '-_') for character in args.run_id):
        raise ValueError('invalid run id')
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol = ROOT / 'research/protocols/rust-contract-logic-v1.json'
    plan = json.loads(protocol.read_text())
    references = []
    for family in plan['families']:
        variables = sorted(family['variables'])
        worlds = [dict(zip(variables, values)) for values in itertools.product([False, True], repeat=len(variables))]
        satisfying = [world for world in worlds if evaluate(family['formula'], world)]
        if not satisfying:
            raise ValueError('vacuous premise')
        for hypothesis in family['hypotheses']:
            positive = [world for world in satisfying if evaluate(hypothesis['formula'], world)]
            negative = [world for world in satisfying if not evaluate(hypothesis['formula'], world)]
            label = 'entailment' if not negative else 'contradiction' if not positive else 'neutral'
            references.append({'id': family['id'] + '/' + hypothesis['id'], 'family': family['id'],
                               'premise': family['premise'], 'hypothesis': hypothesis['text'], 'label': label,
                               'positive_worlds': positive, 'counterexample_worlds': negative})
    if len(references) != 16 or len({row['id'] for row in references}) != 16:
        raise ValueError('unexpected cases')
    shutil.copy2(protocol, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    (output / 'reference.json').write_text(json.dumps(references, indent=2) + '\n')
    reference_digest = sha(output / 'reference.json')
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    model_path = ROOT / 'research/evidence/originals/2026-11-13-nli-weights-01'
    downloads = ROOT / 'research/evidence/runs/2026-11-13-nli-weights-01/downloads.json'
    model_protocol = ROOT / 'research/protocols/nli-cpu-smoke-v1.json'
    model_plan = json.loads(model_protocol.read_text())
    assets = json.loads(downloads.read_text())
    if {path.name for path in model_path.iterdir()} != {record['name'] for record in assets}:
        raise ValueError('unregistered assets')
    for record in assets:
        if sha(model_path / record['name']) != record['sha256']:
            raise ValueError('asset changed')
    if sha(model_path / 'model.safetensors') != model_plan['weight_sha256']:
        raise ValueError('wrong model')
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True, trust_remote_code=False, use_safetensors=True).to(device='cpu', dtype=torch.float32).eval()
    labels = {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
    if model.config.id2label != labels:
        raise ValueError('wrong label order')
    lengths = [len(tokenizer(row['premise'], row['hypothesis'], truncation=False)['input_ids']) for row in references]
    runs = []
    for repeat in (1, 2):
        predictions = []
        with torch.inference_mode():
            for start in range(0, len(references), 8):
                batch = references[start:start + 8]
                inputs = tokenizer([row['premise'] for row in batch], [row['hypothesis'] for row in batch], padding=True, truncation=True, max_length=128, return_tensors='pt')
                logits = model(**inputs).logits
                if tuple(logits.shape) != (len(batch), 3) or not torch.isfinite(logits).all():
                    raise ValueError('invalid logits')
                for row, scores in zip(batch, logits.tolist()):
                    predictions.append({'id': row['id'], 'logits': scores, 'label': labels[max(range(3), key=lambda index: scores[index])]})
        (output / f'predictions-{repeat}.json').write_text(json.dumps(predictions, indent=2) + '\n')
        runs.append(predictions)
    counts = defaultdict(lambda: {'total': 0, 'three_way_correct': 0, 'binary_correct': 0})
    errors = []
    for reference, prediction in zip(references, runs[0]):
        for key in ('overall', reference['family']):
            counts[key]['total'] += 1
            counts[key]['three_way_correct'] += int(reference['label'] == prediction['label'])
            counts[key]['binary_correct'] += int((reference['label'] == 'entailment') == (prediction['label'] == 'entailment'))
        if reference['label'] != prediction['label']:
            errors.append({'id': reference['id'], 'reference': reference['label'], 'prediction': prediction['label']})
    if sha(output / 'reference.json') != reference_digest:
        raise ValueError('reference changed during inference')
    manifest = {'model_revision': model_plan['revision'], 'reference_sha256_before_inference': reference_digest,
                'inputs': {str(path.relative_to(ROOT)): sha(path) for path in (protocol, downloads, model_protocol)},
                'packages': {distribution.metadata['Name']: distribution.version for distribution in importlib.metadata.distributions()},
                'torch': torch.__version__}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    report = {'scope': plan['scope'], 'metrics': dict(counts), 'errors': errors, 'max_input_length': max(lengths),
              'truncated': sum(length > 128 for length in lengths), 'predictions_equal': runs[0] == runs[1],
              'artifact_sha256': {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
