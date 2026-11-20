"""Export fixed source units without tokenization, scoring, or truth labels."""

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'research/evidence/runs/2026-11-05-source-units-v2-verified'
INVENTORY_SHA256 = '43a6df7c84117979c0af773357cd754b879b32cdf2cec66c093fdf101e67a7e0'
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'
FUNCTION_KINDS = {'fn', 'impl_fn', 'trait_fn'}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def extract(source, unit):
    signature = unit['signature_range']
    body = unit['body_range']
    full = unit['range']
    if not (0 <= full[0] <= signature[0] < signature[1] <= body[0] < body[1] <= full[1] <= len(source)):
        raise ValueError('Invalid or inconsistent byte ranges')
    snippet = source[signature[0]:body[1]]
    snippet.decode('utf-8')
    if source[body[0]:body[0] + 1] != b'{' or source[body[1] - 1:body[1]] != b'}':
        raise ValueError('Function body boundary is not braced')
    return snippet, [signature[0], body[1]]


def archive_write(archive, name, content):
    info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'revision': REVISION, 'tokenization': 'not_run',
              'candidate_detection': 'not_run', 'cfg': 'not_evaluated'}
    shutil.copy2(__file__, args.output / 'exporter.py')
    try:
        raw = (INPUT / 'inventory.json').read_bytes()
        if digest(raw) != INVENTORY_SHA256:
            raise ValueError('Inventory identity changed')
        inventory = json.loads(raw)
        upstream = json.loads((INPUT / 'report.json').read_text())
        if upstream['status'] != 'passed_with_limits' or inventory['commit'] != REVISION:
            raise ValueError('Input workflow did not pass or revision changed')
        if upstream['artifacts']['inventory.json'] != digest(raw):
            raise ValueError('Upstream report does not match inventory')
        report['inventory_sha256'] = digest(raw)
        records = []
        identities = set()
        with zipfile.ZipFile(args.output / 'units.zip', 'w') as units_archive, \
                zipfile.ZipFile(args.output / 'sources.zip', 'w') as sources_archive:
            for path, file in sorted(inventory['files'].items()):
                if Path(path).is_absolute() or '..' in Path(path).parts:
                    raise ValueError('Unsafe source path')
                if file['status'] != 'parsed_by_syn':
                    raise ValueError('Unparsed file must not disappear from denominator')
                source = subprocess.check_output(['git', '-C', str(args.repo), 'show', f'{REVISION}:{path}'])
                if digest(source) != file['source_sha256']:
                    raise ValueError('Fixed source does not match inventory')
                archive_write(sources_archive, path, source)
                for unit in file['units']:
                    if unit['kind'] not in FUNCTION_KINDS or unit.get('body_range') is None:
                        continue
                    identity = unit['snapshot_id']
                    if identity in identities:
                        raise ValueError('Duplicate unit ID')
                    identities.add(identity)
                    snippet, span = extract(source, unit)
                    name = identity + '.rs'
                    archive_write(units_archive, name, snippet)
                    ancestors = [file['units'][index] for index in unit['ancestors']]
                    records.append({'id': identity, 'entry': name, 'path': path,
                                    'package': file['physical_package'], 'name': unit['name'],
                                    'kind': unit['kind'], 'range': span,
                                    'start_line': source[:span[0]].count(b'\n') + 1,
                                    'end_line': source[:span[1] - 1].count(b'\n') + 1,
                                    'sha256': digest(snippet), 'source_sha256': digest(source),
                                    'original_range': unit['range'], 'attributes': unit['attributes'],
                                    'ancestor_ids': [parent['snapshot_id'] for parent in ancestors],
                                    'nested_in_function': any(parent['kind'] in FUNCTION_KINDS for parent in ancestors),
                                    'ancestor_attributes': [parent['attributes'] for parent in ancestors],
                                    'file_attributes': file['file_attributes'],
                                    'test_path_hint': file['test_path_hint'], 'cfg': 'not_evaluated'})
        if len(records) != inventory['summary']['functions_with_body']:
            raise ValueError('Function denominator changed')
        (args.output / 'units.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
        report.update({'passed': True, 'files': len(inventory['files']), 'units': len(records),
                       'nested_function_units': sum(record['nested_in_function'] for record in records),
                       'test_path_hint_units': sum(record['test_path_hint'] for record in records),
                       'representation': 'signature start through body end; no attribute/doc prefix; original bytes otherwise unchanged'})
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {path.name: digest(path.read_bytes())
                                    for path in sorted(args.output.iterdir()) if path.is_file()}
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
