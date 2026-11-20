"""Package the fixed subset review queue without method/rank disclosure."""

import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

from prepare_call_view_review import dump, read, require, sha


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
FIRST = RUNS / '2026-11-18-call-subset-ranking-01'
SECOND = RUNS / '2026-11-18-call-subset-ranking-02'
CORPUS = RUNS / '2026-11-05-rust-baseline-corpus-01'
INVENTORY = RUNS / '2026-11-05-source-units-v2-verified/inventory.json'
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'
QUEUE_SHA256 = '17e4b3418155adcd0d7687733f2801a541d054881e15b32d724e9268468f25ca'
REPORT_SHA256 = 'a1d8c53812227a027888373654901238e6a8d261eaf6211136734fae7104707d'
REPEAT_SHA256 = '3a727e1a86b096b3931f3014dd0c300d71acaf7d04875bd27c3c2cc0ca9d6d24'


def preflight():
    require(sha(FIRST / 'review-queue.json') == QUEUE_SHA256, 'First queue changed')
    require(sha(SECOND / 'review-queue.json') == QUEUE_SHA256, 'Second queue differs')
    require(sha(FIRST / 'report.json') == sha(SECOND / 'report.json') == REPORT_SHA256, 'Ranking report changed')
    require(sha(SECOND / 'repeat-check.json') == REPEAT_SHA256, 'Repeat-check changed')
    repeat = read(SECOND / 'repeat-check.json')
    require(repeat['passed'] and repeat['full_score_arrays_equal'], 'Repeats did not pass')
    for name, digest in repeat['compared_artifacts'].items():
        require(sha(FIRST / name) == sha(SECOND / name) == digest, 'Repeated artifact changed: ' + name)
    helper = ROOT / 'scripts/prepare_call_view_review.py'
    require(sha(helper) == sha(RUNS / '2026-11-18-call-view-review-01/runner.py'), 'Original packaging helper changed')
    queue = read(FIRST / 'review-queue.json')
    require(len(queue) == 6 and [row['slot'] for row in queue] == list(range(1, 7)), 'Fixed six order changed')
    require(len({tuple(row['pair']) for row in queue}) == 6, 'Duplicate selected pair')
    corpus_report = read(CORPUS / 'report.json')
    require(corpus_report['revision'] == REVISION, 'Wrong corpus revision')
    ranking_protocol = read(FIRST / 'protocol.json')
    require(sha(CORPUS / 'units.json') == ranking_protocol['inputs']['units']['sha256'], 'Rank/source units differ')
    for name in ('units.json', 'units.zip', 'sources.zip'):
        require(sha(CORPUS / name) == corpus_report['artifacts_sha256'][name], 'Corpus identity mismatch: ' + name)
    require(sha(INVENTORY) == corpus_report['inventory_sha256'], 'Original inventory changed')
    inventory = read(INVENTORY)
    require(inventory['commit'] == REVISION, 'Inventory revision differs')
    units_list = read(CORPUS / 'units.json')
    units = {unit['id']: unit for unit in units_list}
    require(len(units) == len(units_list), 'Duplicate source IDs')
    nodes = {node['snapshot_id']: (path, node)
             for path, file in inventory['files'].items() for node in file['units']}
    prepared = []
    with zipfile.ZipFile(CORPUS / 'units.zip') as snippets, zipfile.ZipFile(CORPUS / 'sources.zip') as sources:
        for row in queue:
            require([member['id'] for member in row['members']] == row['pair'], 'Member order differs')
            members = []
            for queued in row['members']:
                unit = units[queued['id']]
                require(queued == unit, 'Queue unit metadata changed')
                require(not unit['test_path_hint'] and not unit['nested_in_function'], 'Outside frozen subset')
                snippet = snippets.read(unit['entry'])
                source = sources.read(unit['path'])
                require(hashlib.sha256(snippet).hexdigest() == unit['sha256'], 'Snippet hash mismatch')
                require(hashlib.sha256(source).hexdigest() == unit['source_sha256'], 'Full source hash mismatch')
                start, end = unit['range']
                original_start, original_end = unit['original_range']
                require(0 <= original_start <= start < end <= original_end <= len(source), 'Invalid source ranges')
                require(source[start:end] == snippet, 'Exact snippet reconstruction failed')
                source[original_start:original_end].decode('utf-8')
                path, node = nodes[unit['id']]
                require(path == unit['path'] and node['range'] == unit['original_range'], 'Original range differs')
                require([node['signature_range'][0], node['body_range'][1]] == unit['range'], 'Signature/body range differs')
                require(source[:start].count(b'\n') + 1 == unit['start_line'], 'Start line differs')
                require(source[:end - 1].count(b'\n') + 1 == unit['end_line'], 'End line differs')
                attributes = unit['attributes'] + unit['file_attributes']
                attributes += [attribute for group in unit['ancestor_attributes'] for attribute in group]
                for attribute in attributes:
                    attr_start, attr_end = attribute['range']
                    require(source[attr_start:attr_end].decode('utf-8') == attribute['source'], 'Attribute/cfg hint differs')
                members.append((unit, snippet, source))
            prepared.append((row, members))
    paths = [FIRST / 'review-queue.json', FIRST / 'report.json', FIRST / 'protocol.json',
             SECOND / 'review-queue.json', SECOND / 'report.json', SECOND / 'repeat-check.json',
             CORPUS / 'report.json', CORPUS / 'units.json', CORPUS / 'units.zip', CORPUS / 'sources.zip',
             INVENTORY, helper, Path(__file__)]
    return prepared, {str(path.relative_to(ROOT)): sha(path) for path in paths}


def package(output):
    if output.exists():
        raise FileExistsError('Refusing to overwrite existing output: ' + str(output))
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, output / 'runner.py')
    dump(output / 'protocol.json', {
        'scope': 'Package exactly the fixed six queue entries in existing order; no selection or judgments.',
        'source_revision': REVISION, 'queue_sha256': QUEUE_SHA256,
        'ranking_report_sha256': REPORT_SHA256, 'repeat_check_sha256': REPEAT_SHA256,
        'reviewer_fields': 'case_id, source_revision, full original unit metadata, review_files',
        'analyst_only': 'slot, selected_from, rank, score, pair; parent artifacts never enter reviewer ZIP',
        'population_caveat': 'not-test-path-hint and non-nested is not confirmed production',
        'failure_policy': 'Record preflight failures and retain failed output; never overwrite or silently repair.',
        'model_dispatch': False, 'new_labels': False,
    })
    try:
        prepared, hashes = preflight()
    except Exception as error:
        dump(output / 'preflight.json', {'passed': False, 'failures': [f'{type(error).__name__}: {error}']})
        raise
    dump(output / 'preflight.json', {'passed': True, 'failures': [], 'pairs': 6, 'members': 12,
                                    'source_hashes_and_original_ranges_checked': True})
    dump(output / 'freeze.json', hashes)
    shutil.copyfile(FIRST / 'review-queue.json', output / 'queue.json')
    shutil.copyfile(FIRST / 'report.json', output / 'parent-report.json')
    reviewer = output / 'reviewer'
    reviewer.mkdir()
    cases, analyst = [], []
    for serial, (row, prepared_members) in enumerate(prepared, 1):
        case_id = f'case-{serial:03d}'
        folder = reviewer / case_id
        folder.mkdir()
        members = []
        for side, (unit, snippet, source) in zip(('left', 'right'), prepared_members):
            (folder / f'{side}-snippet.rs').write_bytes(snippet)
            (folder / f'{side}-source.rs').write_bytes(source)
            members.append({**unit, 'review_files': {
                'snippet': f'{case_id}/{side}-snippet.rs', 'source': f'{case_id}/{side}-source.rs',
            }})
        cases.append({'case_id': case_id, 'source_revision': REVISION, 'members': members})
        analyst.append({'case_id': case_id, **{key: value for key, value in row.items() if key != 'members'}})
    dump(reviewer / 'cases.json', cases)
    dump(output / 'analyst-only.json', analyst)
    dump(reviewer / 'manifest.json', {
        'schema': 'source-review-package/1', 'source_revision': REVISION, 'cases': 6,
        'artifacts_sha256': {str(path.relative_to(reviewer)): sha(path)
                            for path in sorted(reviewer.rglob('*')) if path.is_file()},
        'limits': ['Full original sources and original metadata only; no semantic judgments.',
                   'cfg and test hints are not configuration evaluation or confirmed production status.',
                   'Method-hidden presentation, not access control or independent test-set evidence.'],
    })
    with zipfile.ZipFile(output / 'reviewer.zip', 'w') as archive:
        for path in sorted(reviewer.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(reviewer)), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    summary = {
        'status': 'ready_for_independent_source_review', 'cases_prepared': 6, 'cases_reviewed': 0,
        'source_copies': 12, 'snippet_copies': 12, 'fixed_queue_order_preserved': True,
        'preflight_passed': True, 'preflight_failures': [], 'model_runs': 0, 'new_labels': 0,
        'reviewer_package_sha256': sha(output / 'reviewer.zip'),
        'reviewer_manifest_sha256': sha(reviewer / 'manifest.json'),
        'analyst_materials': ['analyst-only.json', 'queue.json', 'parent-report.json', 'freeze.json', 'protocol.json'],
        'artifacts_sha256': {str(path.relative_to(output)): sha(path)
                            for path in sorted(output.rglob('*')) if path.is_file()},
    }
    dump(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    summary = package(args.output.resolve())
    print({key: value for key, value in summary.items() if key != 'artifacts_sha256'})


if __name__ == '__main__':
    main()
