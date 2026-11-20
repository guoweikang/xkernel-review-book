"""Verify selection without evaluating candidate semantics."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    folder = args.folder
    report = json.loads((folder / 'report.json').read_text())
    for name, digest in report['artifact_sha256'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    frozen = json.loads((folder / 'frozen.json').read_text())
    plan = json.loads((folder / 'protocol.json').read_text())
    root = Path(__file__).resolve().parents[1]
    for relative, digest in frozen['input_sha256'].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest
    candidates = json.loads((root / plan['population']).read_text())
    selected = json.loads((folder / 'selection.json').read_text())
    ordered = sorted(candidates, key=lambda pair: hashlib.sha256(('crate-contract-next-v1:' + ':'.join(sorted(member['id'] for member in pair['members']))).encode()).hexdigest())
    expected = []
    used = set()
    eligible = 0
    for pair in ordered:
        members = pair['members']
        if any(member['test_path_hint'] or member['nested_in_function'] or member['path'] in frozen['excluded_paths'] for member in members):
            continue
        eligible += 1
        paths = {member['path'] for member in members}
        if paths & used or len(expected) >= plan['budget']:
            continue
        expected.append(pair)
        used.update(paths)
    assert selected == expected
    assert report['population_pairs'] == len(candidates)
    assert report['selected_pairs'] == len(selected)
    assert report['eligibility_before_file_diversity'] == eligible
    audit = json.loads((folder / 'audit.json').read_text())
    assert len(audit) == len(candidates)
    assert {tuple(row['file_ids']) for row in audit} == {tuple(pair['file_ids']) for pair in candidates}
    assert [row['file_ids'] for row in audit if row['selected']] == [pair['file_ids'] for pair in selected]
    for index, pair in enumerate(selected, 1):
        for member_index, member in enumerate(pair['members'], 1):
            for suffix, key in [('unit.rs', 'sha256'), ('source.rs', 'source_sha256')]:
                path = folder / f'pair-{index}-{member_index}-{suffix}'
                assert hashlib.sha256(path.read_bytes()).hexdigest() == member[key]
    print(json.dumps({'population': len(candidates), 'eligible': eligible, 'selected': len(selected),
                      'deterministic_selection_verified': True, 'blind_test': False}))


if __name__ == '__main__':
    main()
