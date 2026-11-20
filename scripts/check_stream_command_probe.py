"""Verify archived traces and reject deliberately corrupted observations."""

import argparse
import copy
import json

from run_stream_command_probe import ROOT, check, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    folder = ROOT / 'research/evidence/runs' / args.run_id
    report = json.loads((folder / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert sha(folder / name) == expected, name
    files = sorted(folder.glob('*-execute.stdout'))
    assert len(files) == 4
    for path in files:
        assert path.read_bytes() == files[0].read_bytes()
        check([json.loads(line) for line in path.read_text().splitlines()])
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    for field, value in [('result', 'Ok(99)'), ('remaining', 99), ('position', 99), ('calls', [])]:
        corrupted = copy.deepcopy(rows)
        corrupted[0][field] = value
        try:
            check(corrupted)
        except AssertionError:
            pass
        else:
            raise AssertionError(f'corruption accepted: {field}')
    corrupted = copy.deepcopy(rows)
    corrupted[0]['calls'][0]['payload'][0] = 255
    try:
        check(corrupted)
    except AssertionError:
        pass
    else:
        raise AssertionError('payload corruption accepted')
    print('PASS: artifact hashes, four identical traces, frozen outcomes, five corruption controls')


if __name__ == '__main__':
    main()
