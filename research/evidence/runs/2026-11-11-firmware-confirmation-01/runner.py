"""Extract bounded syntax evidence; never classify semantic ownership automatically."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(binary, source):
    process = subprocess.run([str(binary)], input=source, capture_output=True, check=True)
    return json.loads(process.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol_path = ROOT / 'research/protocols/firmware-confirmation-v1.json'
    protocol = json.loads(protocol_path.read_text())
    source_run = ROOT / protocol['source_run']
    report = json.loads((source_run / 'report.json').read_text())
    units_binary = ROOT / '.build/source-workflow-target/debug/rust-syntax-probe'
    calls_binary = ROOT / '.build/rust-call-probe/debug/rust-call-probe'

    def calls(source):
        result = invoke(calls_binary, source)
        names = set()
        for site in result['sites']:
            start, end = site['range']
            assert 0 <= start < end <= len(source)
            site['source_text'] = source[start:end].decode()
            assert site['target_resolution'] == 'unresolved'
            if site['kind'] != 'opaque_macro':
                names.add(site['name'])
        result['signals'] = sorted(key for key, terms in protocol['lexical_signals'].items()
                                   if names.intersection(terms))
        return result

    controls = []
    for fixture in protocol['controls']:
        actual = calls(fixture['source'].encode())
        assert actual['status'] == fixture.get('status', 'parsed'), fixture['name']
        assert actual['signals'] == sorted(fixture['signals']), fixture['name']
        for key, predicate in [
            ('opaque_macros', lambda site: site['kind'] == 'opaque_macro'),
            ('deferred_sites', lambda site: site['deferred_depth'] > 0),
        ]:
            if key in fixture:
                assert sum(predicate(site) for site in actual['sites']) == fixture[key]
        controls.append({'fixture': fixture, 'actual': actual})

    records, missing = [], []
    for label, snapshot in report['snapshots'].items():
        known_files = {item['path']: item for item in snapshot['files']}
        for relative, names in protocol['files'].items():
            if relative not in known_files:
                missing.append({'snapshot': label, 'path': relative, 'reason': 'file_absent', 'names': names})
                continue
            path = source_run / label / relative
            assert digest(path) == known_files[relative]['sha256']
            source = path.read_bytes()
            units = invoke(units_binary, source)
            assert units['status'] == 'parsed_by_syn'
            for name in names:
                matched = [unit for unit in units['units'] if unit.get('name') == name
                           and unit['kind'] in {'fn', 'impl_fn'}]
                if not matched:
                    missing.append({'snapshot': label, 'path': relative, 'reason': 'function_absent', 'names': [name]})
                    continue
                if len(matched) != 1:
                    raise ValueError(f'Ambiguous function selector: {label}/{relative}/{name}')
                unit = matched[0]
                start = unit['signature_range'][0]
                end = unit['body_range'][1]
                assert 0 <= start < end <= len(source)
                fragment = source[start:end]
                actual = calls(fragment)
                assert actual['status'] == 'parsed'
                for site in actual['sites']:
                    offset = start + site['range'][0]
                    site['file_range'] = [offset, start + site['range'][1]]
                    site['line'] = source[:offset].count(b'\n') + 1
                records.append({'snapshot': label, 'commit': report['revisions'][label],
                                'path': relative, 'name': name, 'range': [start, end],
                                'source_sha256': digest(path),
                                'fragment_sha256': hashlib.sha256(fragment).hexdigest(),
                                'fragment': fragment.decode(), **actual})
    for name, content in [('calls.json', records), ('missing.json', missing), ('controls.json', controls)]:
        (args.output / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(protocol_path, args.output / 'protocol.json')
    shutil.copyfile(__file__, args.output / 'runner.py')
    summary = {
        'schema': 'firmware-syntax-evidence/1', 'kind': protocol['kind'],
        'source_report_sha256': digest(source_run / 'report.json'),
        'binaries': {str(path.relative_to(ROOT)): digest(path) for path in (units_binary, calls_binary)},
        'units': len(records), 'controls_passed': len(controls), 'missing': missing,
        'per_snapshot': dict(Counter(record['snapshot'] for record in records)),
        'resolved_edges': 0, 'ownership_classifier': False, 'kernel_tests_run': False,
        'artifact_sha256': {path.name: digest(path) for path in args.output.iterdir() if path.is_file()},
    }
    (args.output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
