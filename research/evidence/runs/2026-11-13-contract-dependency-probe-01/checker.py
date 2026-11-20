"""Independently check archived parser output integrity, not semantic accuracy."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    folder = parser.parse_args().folder
    report = json.loads((folder / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected, name
    texts = json.loads((folder / 'texts.json').read_text())
    rows = json.loads((folder / 'parses-1.json').read_text())
    assert (folder / 'parses-1.json').read_bytes() == (folder / 'parses-2.json').read_bytes()
    assert len(rows) == len(texts) == report['unique_texts']
    count = 0
    for index, row in enumerate(rows):
        assert row['text_index'] == index
        tokens = row['tokens']
        previous_end = 0
        for token_index, token in enumerate(tokens):
            assert token['id'] == token_index
            assert previous_end <= token['start'] < token['end'] <= len(texts[index])
            assert texts[index][token['start']:token['end']] == token['text']
            previous_end = token['end']
            visited = set()
            position = token_index
            while True:
                assert position not in visited
                visited.add(position)
                head = tokens[position]['head']
                assert 0 <= head < len(tokens)
                if head == position:
                    assert tokens[position]['dependency'] == 'ROOT'
                    break
                position = head
        covered = []
        for start, end in row['sentences']:
            assert 0 <= start < end <= len(tokens)
            covered.extend(range(start, end))
        assert covered == list(range(len(tokens)))
        count += len(tokens)
    assert count == report['tokens_per_pass']
    assert report['accuracy_measured'] is False
    print(json.dumps({'texts_checked': len(texts), 'tokens_checked': count,
                      'repeat_identical': True, 'semantic_accuracy_checked': False}))


if __name__ == '__main__':
    main()
