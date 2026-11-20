"""Preserve a public parser's raw outputs before designing relation extraction."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil

import spacy

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol = ROOT / 'research/protocols/contract-dependency-probe-v1.json'
    plan = json.loads(protocol.read_text())
    source = ROOT / plan['input']
    source_report = json.loads((source.parent / 'report.json').read_text())
    if sha(source) != source_report['artifact_sha256']['protocol.json']:
        raise ValueError('parent protocol changed')
    if spacy.__version__ != plan['spacy'] or importlib.metadata.version(plan['model']) != plan['model_version']:
        raise ValueError('unexpected parser version')
    texts = []
    bindings = []
    for family in json.loads(source.read_text())['families']:
        for kind, identity, text in [('premise', family['id'], family['premise'])] + [('hypothesis', family['id']+'/'+row['id'], row['text']) for row in family['hypotheses']]:
            if text not in texts:
                texts.append(text)
            bindings.append({'kind': kind, 'id': identity, 'text_index': texts.index(text)})
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    (folder / 'texts.json').write_text(json.dumps(texts, indent=2) + '\n')
    (folder / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    nlp = spacy.load(plan['model'], exclude=['ner'])
    model_dir = Path(nlp.path)
    manifest = {'inputs': {str(path.relative_to(ROOT)): sha(path) for path in (source, protocol)},
                'model_install_origin': importlib.metadata.distribution(plan['model']).read_text('direct_url.json'),
                'packages': {distribution.metadata['Name']: distribution.version for distribution in importlib.metadata.distributions()},
                'pipeline': nlp.pipe_names, 'model_meta': nlp.meta,
                'model_files': {str(path.relative_to(model_dir)): sha(path) for path in sorted(model_dir.rglob('*')) if path.is_file()}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for repeat in (1, 2):
        records = []
        for text_index, doc in enumerate(nlp.pipe(texts, batch_size=8)):
            tokens = []
            for token in doc:
                if texts[text_index][token.idx:token.idx+len(token)] != token.text:
                    raise ValueError('token span differs')
                seen = set()
                current = token
                while current.head.i != current.i:
                    if current.i in seen or not 0 <= current.head.i < len(doc):
                        raise ValueError('invalid dependency tree')
                    seen.add(current.i)
                    current = current.head
                tokens.append({'id': token.i, 'text': token.text, 'start': token.idx, 'end': token.idx+len(token),
                               'lemma': token.lemma_, 'pos': token.pos_, 'morph': str(token.morph), 'dependency': token.dep_, 'head': token.head.i})
            records.append({'text_index':text_index, 'tokens':tokens, 'sentences':[[sentence.start,sentence.end] for sentence in doc.sents]})
        path = folder / f'parses-{repeat}.json'
        path.write_text(json.dumps(records, indent=2) + '\n')
        if repeat > 1 and path.read_bytes() != (folder / 'parses-1.json').read_bytes():
            raise ValueError('repeat differs')
    report = {'scope':plan['scope'], 'unique_texts':len(texts), 'bindings':len(bindings), 'passes':2,
              'tokens_per_pass':sum(len(row['tokens']) for row in records), 'repeat_identical':True,
              'logical_extractions':0, 'accuracy_measured':False,
              'artifact_sha256':{path.name:sha(path) for path in sorted(folder.iterdir()) if path.is_file()}}
    (folder / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='artifact_sha256'},indent=2))


if __name__ == '__main__':
    main()
