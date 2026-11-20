"""Validate raw SRL records and spans without assigning semantic truth labels."""

import argparse
import hashlib
import json
from pathlib import Path


def check_batches(batches, expected_ids):
    identities = []
    records = []
    for batch in batches:
        output = batch['output']
        tokens, frames = output['tok'], output['srl']
        if len(tokens) != len(frames) or len(tokens) != len(batch['ids']):
            raise ValueError('output count mismatch')
        for identity, sentence_tokens, sentence_frames in zip(batch['ids'], tokens, frames, strict=True):
            identities.append(identity)
            spans = 0
            labels = {}
            for frame in sentence_frames:
                predicates = 0
                for text, label, start, end in frame:
                    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(sentence_tokens):
                        raise ValueError('invalid token span')
                    if text != ' '.join(sentence_tokens[start:end]):
                        raise ValueError('span text mismatch')
                    predicates += label == 'PRED'
                    labels[label] = labels.get(label, 0) + 1
                    spans += 1
                if predicates != 1:
                    raise ValueError('frame predicate count')
            records.append({'id': identity, 'tokens': len(sentence_tokens), 'frames': len(sentence_frames), 'spans': spans, 'labels': labels})
    if identities != expected_ids or len(set(identities)) != len(identities):
        raise ValueError('IDs lost or reordered')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    if not report['success'] or report['inference_passes'] != 2:
        raise ValueError('incomplete run')
    for name, expected in report['artifact_sha256'].items():
        with (folder / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError(f'changed artifact: {name}')
    identities = [row['id'] for row in json.loads((folder / 'inputs.json').read_text())]
    repeats = [check_batches(json.loads((folder / f'raw-{repeat}.json').read_text()), identities) for repeat in (1, 2)]
    identical = (folder / 'raw-1.json').read_bytes() == (folder / 'raw-2.json').read_bytes()
    if identical != report['repeat_identical']:
        raise ValueError('repeat report mismatch')
    fixture = [{'ids': ['control'], 'output': {'tok': [['We', 'read']], 'srl': [[[['We', 'ARG0', 0, 1], ['read', 'PRED', 1, 2]]]]}}]
    check_batches(fixture, ['control'])
    rejected = 0
    for mode in ('span', 'text', 'predicate', 'id'):
        invalid = json.loads(json.dumps(fixture))
        role = invalid[0]['output']['srl'][0][0][1]
        if mode == 'span':
            role[3] = 99
        elif mode == 'text':
            role[0] = 'wrong'
        elif mode == 'predicate':
            role[1] = 'ARG1'
        else:
            invalid[0]['ids'][0] = 'unexpected'
        try:
            check_batches(invalid, ['control'])
        except ValueError:
            rejected += 1
        else:
            raise AssertionError(mode)
    print(json.dumps({'records_each_pass': repeats, 'repeat_identical': identical,
                      'negative_controls_rejected': rejected, 'semantic_accuracy_checked': False}, indent=2))


if __name__ == '__main__':
    main()
