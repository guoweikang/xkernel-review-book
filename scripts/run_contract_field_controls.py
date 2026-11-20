"""Run a frozen, deliberately narrow dependency proxy on development controls."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil

import spacy

from score_contract_fields import FIELDS, score

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(doc):
    empty = dict.fromkeys(FIELDS)
    roots = [token for token in doc if token.dep_ == 'ROOT']
    if len(roots) != 1 or roots[0].pos_ != 'VERB':
        return empty, 'not_one_verbal_root'
    root = roots[0]
    if any(token.dep_ in {'ccomp', 'xcomp', 'advcl', 'conj', 'relcl'} for token in doc):
        return empty, 'subclause_or_coordination'
    if root.lemma_.lower() in {'state', 'report', 'require', 'demand'}:
        return empty, 'reporting_or_normative_root'
    active = [token for token in root.children if token.dep_ == 'nsubj']
    objects = [token for token in root.children if token.dep_ == 'dobj']
    passive = [token for token in root.children if token.dep_ == 'nsubjpass']
    agents = [child for token in root.children if token.dep_ == 'agent' for child in token.children if child.dep_ == 'pobj']
    if len(active) == len(objects) == 1 and not passive:
        actor, patient = active[0], objects[0]
    elif len(passive) == len(agents) == 1 and not active:
        actor, patient = agents[0], passive[0]
    else:
        return empty, 'unsupported_argument_shape'
    return {'actor': actor.lemma_.lower(), 'action': root.lemma_.lower(),
            'object': patient.lemma_.lower(),
            'polarity': 'negative' if any(token.dep_ == 'neg' for token in root.children) else 'positive',
            'force': 'assertion', 'condition': 'none'}, 'simple_transitive_proxy'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol = ROOT / 'research/protocols/contract-field-controls-v1.json'
    cases_path = ROOT / 'research/protocols/contract-field-cases-v1.json'
    plan = json.loads(protocol.read_text())
    cases = json.loads(cases_path.read_text())
    if spacy.__version__ != plan['spacy'] or importlib.metadata.version(plan['model']) != plan['model_version']:
        raise ValueError('unexpected model or parser version')
    for source, name in ((protocol, 'protocol.json'), (cases_path, 'cases.json'), (Path(__file__), 'runner.py'), (ROOT / 'scripts/score_contract_fields.py', 'scorer.py')):
        shutil.copy2(source, folder / name)
    inputs = [{'id': row['id'], 'text': row['text']} for row in cases]
    (folder / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    nlp = spacy.load(plan['model'], exclude=['ner'])
    model_dir = Path(nlp.path)
    manifest = {'model_files': {str(path.relative_to(model_dir)): sha(path) for path in sorted(model_dir.rglob('*')) if path.is_file()},
                'packages': {dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()},
                'pipeline': nlp.pipe_names, 'model_meta': nlp.meta}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for repeat in (1, 2):
        predictions, parses = [], []
        for row, doc in zip(inputs, nlp.pipe([row['text'] for row in inputs], batch_size=8), strict=True):
            fields, reason = extract(doc)
            predictions.append({'id': row['id'], 'fields': fields, 'reason': reason})
            parses.append({'id': row['id'], 'tokens': [{'id': token.i, 'text': token.text, 'start': token.idx, 'end': token.idx + len(token), 'lemma': token.lemma_, 'pos': token.pos_, 'dep': token.dep_, 'head': token.head.i} for token in doc]})
        for name, records in (('predictions', predictions), ('parses', parses)):
            output = folder / f'{name}-{repeat}.json'
            output.write_text(json.dumps(records, indent=2) + '\n')
            if repeat == 2 and output.read_bytes() != (folder / f'{name}-1.json').read_bytes():
                raise ValueError('repeat differs')
    result = score(cases, predictions)
    (folder / 'scores.json').write_text(json.dumps(result, indent=2) + '\n')
    report = {'scope': plan['status'], 'repeat_identical': True,
              'artifact_sha256': {path.name: sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'records': result['records'], 'exact_records': result['exact_records'], 'pooled': result['counts']['pooled']}, indent=2))


if __name__ == '__main__':
    main()
