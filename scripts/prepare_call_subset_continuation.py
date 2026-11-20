"""Freeze remaining original-top20 slots, then package exact source evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
RANKING = RUNS / '2026-11-18-call-subset-ranking-01'
CORPUS = RUNS / '2026-11-05-rust-baseline-corpus-01'
PROTOCOL = ROOT / 'research/protocols/call-subset-continuation-v1.json'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def select(output, exposure=None):
    output.mkdir(parents=True, exist_ok=False)
    paths = [RANKING / name for name in ('code-top20.json', 'call_set-top20.json',
             'exclusions.json', 'review-queue.json', 'units.json', 'protocol.json')]
    paths += [PROTOCOL, Path(__file__), CORPUS / 'report.json', CORPUS / 'units.json',
              CORPUS / 'units.zip', CORPUS / 'sources.zip']
    report = read(CORPUS / 'report.json')
    for name in ('units.json', 'units.zip', 'sources.zip'):
        assert digest(CORPUS / name) == report['artifacts_sha256'][name]
    assert report['revision'] == read(PROTOCOL)['source_revision']
    repeat = RUNS / '2026-11-18-call-subset-ranking-02'
    for name in ('code-top20.json', 'call_set-top20.json', 'exclusions.json', 'review-queue.json'):
        assert digest(RANKING / name) == digest(repeat / name)
    original_queue = read(RANKING / 'review-queue.json')
    prior = {tuple(row['pair']): row['reasons'] for row in read(RANKING / 'exclusions.json')}
    for row in original_queue:
        prior.setdefault(tuple(sorted(row['pair'])), []).append('first_subset_review')
    if exposure is not None:
        audit = read(exposure)
        for source in audit['sources']:
            assert digest(ROOT / source['path']) == source['sha256']
            paths.append(ROOT / source['path'])
        paths.append(exposure)
        for row in audit['excluded_pairs']:
            prior.setdefault(tuple(sorted(row['pair'])), []).extend(row['sources'])
    closed = {identity for row in original_queue if row['slot'] in (1, 4, 6)
              for identity in row['pair']}
    rankings = {method: read(RANKING / f'{method}-top20.json') for method in ('call_set', 'code')}
    sets = {method: {tuple(sorted(row[1:])) for row in rows} for method, rows in rankings.items()}
    streams = {}
    ledger = []
    for method, rows in rankings.items():
        streams[method] = []
        other = 'code' if method == 'call_set' else 'call_set'
        for rank, (score, first, second) in enumerate(rows, 1):
            pair = tuple(sorted((first, second)))
            reasons = list(prior.get(pair, []))
            if pair in sets[other]:
                reasons.append('shared_top20')
            if closed.intersection(pair):
                reasons.append('touches_closed_mechanism_unit')
            row = {'method': method, 'rank': rank, 'score': score, 'pair': pair, 'excluded_by': reasons}
            ledger.append(row)
            if not reasons:
                streams[method].append(row)
    queue = []
    empty = []
    for slot, method in enumerate(read(PROTOCOL)['slots'], 1):
        if streams[method]:
            queue.append(dict(streams[method].pop(0), slot=slot, case_id=f'case-{slot:03d}'))
        else:
            empty.append({'slot': slot, 'method': method, 'reason': 'remaining_exclusive_top20_exhausted'})
    shutil.copyfile(PROTOCOL, output / 'protocol.json')
    shutil.copyfile(__file__, output / 'runner.py')
    save(output / 'selection.json', {'queue': queue, 'unfilled': empty, 'ledger': ledger,
                                    'closed_unit_ids': sorted(closed), 'known_excluded_pairs': len(prior)})
    save(output / 'freeze.json', {'files': {str(path.relative_to(ROOT)): digest(path) for path in paths},
                                 'selection_sha256': digest(output / 'selection.json')})
    print(json.dumps({'selected': len(queue), 'unfilled': empty}))


def package(output):
    frozen = read(output / 'freeze.json')
    for name, identity in frozen['files'].items():
        assert digest(ROOT / name) == identity, name
    assert digest(output / 'selection.json') == frozen['selection_sha256']
    units = {unit['id']: unit for unit in read(CORPUS / 'units.json')}
    reviewer = output / 'reviewer'
    reviewer.mkdir(exist_ok=False)
    cases = []
    with zipfile.ZipFile(CORPUS / 'sources.zip') as sources, zipfile.ZipFile(CORPUS / 'units.zip') as snippets:
        for row in read(output / 'selection.json')['queue']:
            directory = reviewer / row['case_id']
            directory.mkdir()
            members = []
            for side, identity in zip(('left', 'right'), row['pair']):
                unit = units[identity]
                source = sources.read(unit['path'])
                snippet = snippets.read(unit['entry'])
                assert hashlib.sha256(source).hexdigest() == unit['source_sha256']
                assert hashlib.sha256(snippet).hexdigest() == unit['sha256']
                start, end = unit['range']
                assert source[start:end] == snippet
                assert source[:start].count(b'\n') + 1 == unit['start_line']
                assert source[:end-1].count(b'\n') + 1 == unit['end_line']
                (directory / f'{side}-source.rs').write_bytes(source)
                (directory / f'{side}-snippet.rs').write_bytes(snippet)
                members.append(dict(unit, source_file=f'{row["case_id"]}/{side}-source.rs',
                                    snippet_file=f'{row["case_id"]}/{side}-snippet.rs'))
            cases.append({'case_id': row['case_id'], 'source_revision': read(PROTOCOL)['source_revision'], 'members': members})
    save(reviewer / 'cases.json', cases)
    save(output / 'package-hashes.json', {str(path.relative_to(output)): digest(path)
                                        for path in reviewer.rglob('*') if path.is_file()})
    print(f'Packaged {len(cases)} cases with verified source hashes and byte ranges')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['select', 'package'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--exposure', type=Path)
    args = parser.parse_args()
    if args.operation == 'select':
        select(RUNS / args.run, args.exposure.resolve() if args.exposure else None)
    else:
        package(RUNS / args.run)
