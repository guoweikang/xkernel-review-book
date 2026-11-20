"""Package the six preselected pairs without exposing ranking metadata."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/evidence/runs'
PARENT = RUNS / '2026-11-18-call-view-ranking-01'
CORPUS = RUNS / '2026-11-05-rust-baseline-corpus-01'
SCOPE = RUNS / '2026-11-16-discovery-common-scope-01'
INVENTORY = RUNS / '2026-11-05-source-units-v2-verified/inventory.json'
QUEUE_SHA256 = 'd6f8d8cba3560acc080ee3d6594ada6b3adc23760a4616923f7365629f737a66'
REPORT_SHA256 = '2a79f0aa3931f1e3b31de1f8b350aa08839490038e987cd9869a706a8b3ec729'
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def package(output):
    if output.exists():
        raise FileExistsError('Refusing to overwrite existing output: ' + str(output))
    queue_path = PARENT / 'review-queue.json'
    require(sha(queue_path) == QUEUE_SHA256, 'Preselected queue changed')
    require(sha(PARENT / 'report.json') == REPORT_SHA256, 'Parent report changed')
    queue = read(queue_path)
    require(len(queue) == 6, 'Expected exactly six preselected pairs')
    pairs = [tuple(row['pair']) for row in queue]
    require(all(len(pair) == 2 and pair[0] < pair[1] for pair in pairs), 'Invalid canonical pair')
    require(len(set(pairs)) == 6, 'Duplicate pair')
    corpus_report = read(CORPUS / 'report.json')
    scope = read(SCOPE / 'protocol.json')
    require(corpus_report['revision'] == REVISION, 'Wrong source revision')
    require(sha(CORPUS / 'units.json') == scope['inputs']['units']['sha256'], 'Common-scope units changed')
    for name in ('units.json', 'units.zip', 'sources.zip'):
        require(sha(CORPUS / name) == corpus_report['artifacts_sha256'][name], 'Corpus identity changed: ' + name)
    require(sha(INVENTORY) == corpus_report['inventory_sha256'], 'Inventory changed')
    inventory = read(INVENTORY)
    require(inventory['commit'] == REVISION, 'Inventory revision mismatch')
    units_list = read(CORPUS / 'units.json')
    units = {unit['id']: unit for unit in units_list}
    require(len(units) == len(units_list), 'Duplicate unit ID')
    source_nodes = {node['snapshot_id']: (path, node)
                    for path, file in inventory['files'].items() for node in file['units']}
    prepared = []
    with zipfile.ZipFile(CORPUS / 'units.zip') as snippets, zipfile.ZipFile(CORPUS / 'sources.zip') as sources:
        for row in queue:
            require([member['id'] for member in row['members']] == row['pair'], 'Queue member order mismatch')
            members = []
            for queued in row['members']:
                identity = queued['id']
                unit = units[identity]
                require(queued == unit, 'Queue metadata differs from frozen unit: ' + identity)
                snippet = snippets.read(unit['entry'])
                source = sources.read(unit['path'])
                require(hashlib.sha256(snippet).hexdigest() == unit['sha256'], 'Snippet hash mismatch')
                require(hashlib.sha256(source).hexdigest() == unit['source_sha256'], 'Full-source hash mismatch')
                start, end = unit['range']
                original_start, original_end = unit['original_range']
                require(0 <= original_start <= start < end <= original_end <= len(source), 'Invalid original/source range')
                require(source[start:end] == snippet, 'Snippet does not match source range')
                source[original_start:original_end].decode('utf-8')
                source_path, node = source_nodes[identity]
                require(source_path == unit['path'] and node['range'] == unit['original_range'], 'Original node range mismatch')
                require([node['signature_range'][0], node['body_range'][1]] == unit['range'], 'Signature/body range mismatch')
                require(source[:start].count(b'\n') + 1 == unit['start_line'], 'Start line mismatch')
                require(source[:end - 1].count(b'\n') + 1 == unit['end_line'], 'End line mismatch')
                attributes = unit['attributes'] + unit['file_attributes']
                attributes += [attribute for group in unit['ancestor_attributes'] for attribute in group]
                for attribute in attributes:
                    attr_start, attr_end = attribute['range']
                    require(source[attr_start:attr_end].decode('utf-8') == attribute['source'], 'Attribute hint source mismatch')
                members.append((unit, snippet, source))
            prepared.append((row, members))
    output.mkdir(parents=True, exist_ok=False)
    reviewer = output / 'reviewer'
    reviewer.mkdir()
    cases = []
    analyst = []
    for serial, (row, prepared_members) in enumerate(prepared, 1):
        case_id = f'case-{serial:03d}'
        folder = reviewer / case_id
        folder.mkdir()
        members = []
        for side, (unit, snippet, source) in zip(('left', 'right'), prepared_members):
            (folder / f'{side}-snippet.rs').write_bytes(snippet)
            (folder / f'{side}-source.rs').write_bytes(source)
            members.append({**unit, 'review_files': {
                'snippet': f'{case_id}/{side}-snippet.rs',
                'source': f'{case_id}/{side}-source.rs',
            }})
        cases.append({'case_id': case_id, 'source_revision': REVISION, 'members': members})
        analyst.append({'case_id': case_id, 'queue_index': serial - 1, 'unit_ids': row['pair'],
                        'selected_from': row['selected_from'], 'rank': row['rank']})
    dump(reviewer / 'cases.json', cases)
    reviewer_hashes = {str(path.relative_to(reviewer)): sha(path)
                       for path in sorted(reviewer.rglob('*')) if path.is_file()}
    dump(reviewer / 'manifest.json', {
        'schema': 'source-review-package/1', 'source_revision': REVISION,
        'cases': 6, 'member_occurrences': 12, 'artifacts_sha256': reviewer_hashes,
        'limits': ['cfg hints are preserved, not evaluated.',
                   'Physical file/package context does not establish resolved call targets.',
                   'No semantic judgments or reference labels supplied.'],
    })
    with zipfile.ZipFile(output / 'reviewer.zip', 'w') as archive:
        for path in sorted(reviewer.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(reviewer)), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    dump(output / 'analyst-only.json', analyst)
    shutil.copyfile(__file__, output / 'runner.py')
    dump(output / 'freeze.json', {
        'source_revision': REVISION, 'queue': {'path': str(queue_path.relative_to(ROOT)), 'sha256': QUEUE_SHA256},
        'parent_report_sha256': REPORT_SHA256, 'scope_protocol_sha256': sha(SCOPE / 'protocol.json'),
        'inventory_sha256': sha(INVENTORY), 'corpus_report_sha256': sha(CORPUS / 'report.json'),
        'source_inputs': {name: sha(CORPUS / name) for name in ('units.json', 'units.zip', 'sources.zip')},
        'runner_sha256': sha(Path(__file__)),
    })
    summary = {
        'cases_prepared': 6, 'cases_reviewed': 0, 'member_occurrences': 12,
        'full_source_copies': 12, 'snippet_copies': 12,
        'cfg': 'not_evaluated', 'model_runs': 0, 'new_reference_labels': 0,
        'reviewer_package_sha256': sha(output / 'reviewer.zip'),
        'reviewer_manifest_sha256': sha(reviewer / 'manifest.json'),
        'limits': ['Only reviewer/ or reviewer.zip is intended for review; analyst-only.json stays outside.',
                   'Method-hidden packaging is not access control or held-out evaluation.',
                   'Preselected pairs and their order are preserved; no reselection or semantic judgment.'],
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
    print(json.dumps({key: value for key, value in summary.items() if key != 'artifacts_sha256'}))


if __name__ == '__main__':
    main()
