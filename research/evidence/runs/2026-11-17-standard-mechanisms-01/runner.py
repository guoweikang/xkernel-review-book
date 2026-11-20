import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from check_syn_probe import parse
from export_rust_baseline_corpus import extract


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/standard-mechanism-screen-v1.json'
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / 'research/evidence/runs' / protocol['input']
    report = json.loads((parent / 'report.json').read_text())
    for name, expected in report['artifacts_sha256'].items():
        assert sha(parent / name) == expected
    upstream_path = ROOT / 'research/evidence/runs' / protocol['identity_verification'] / 'report.json'
    upstream = json.loads(upstream_path.read_text())
    assert upstream['status'] == 'verified' and not upstream['mismatches']
    archive_path = ROOT / 'research/evidence' / report['archive']
    assert sha(archive_path) == report['archive_sha256']
    records = json.loads((parent / 'inventory.json').read_text())
    shutil.copyfile(protocol_path, run / 'protocol.json')
    shutil.copyfile(__file__, run / 'runner.py')
    helper_names = ['check_syn_probe.py', 'export_rust_baseline_corpus.py']
    for name in helper_names:
        shutil.copyfile(ROOT / 'scripts' / name, run / name)
    dump(run / 'freeze.json', {'binary': str(binary), 'binary_sha256': sha(binary), 'archive': str(archive_path), 'archive_sha256': sha(archive_path), 'inventory_sha256': sha(parent / 'inventory.json'), 'upstream_report_sha256': sha(upstream_path), 'compiler': subprocess.check_output(['rustc', '+1.95.0', '-Vv'], text=True), 'helpers': {name: sha(run / name) for name in helper_names}, 'tool_sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted((ROOT / 'research/tools/rust-syntax-probe').rglob('*')) if path.is_file() and 'target' not in path.parts}})
    files, units = [], []
    parsed_dir = run / 'parsed'
    parsed_dir.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        for record in records:
            if not record['path'].endswith('.rs'):
                continue
            source = archive.read(record['path'])
            assert hashlib.sha256(source).hexdigest() == record['sha256']
            try:
                result = parse(binary, source)
            except (ValueError, KeyError, UnicodeError, subprocess.SubprocessError) as error:
                result = {'status': 'adapter_failure', 'units': [], 'diagnostics': [{'message': str(error)}]}
            parsed_name = hashlib.sha256(record['path'].encode()).hexdigest() + '.json'
            dump(parsed_dir / parsed_name, result)
            files.append({'path': record['path'], 'source_sha256': record['sha256'], 'status': result['status'], 'parsed': 'parsed/' + parsed_name, 'diagnostics': result['diagnostics'], 'unit_kinds': dict(Counter(unit['kind'] for unit in result['units']))})
            for index, unit in enumerate(result['units']):
                if unit['kind'] not in {'fn', 'impl_fn', 'trait_fn'} or unit.get('body_range') is None:
                    continue
                snippet, span = extract(source, unit)
                identity = hashlib.sha256(json.dumps([upstream['commit'], record['path'], record['sha256'], index, span]).encode()).hexdigest()
                units.append({'id': identity, 'path': record['path'], 'package': record['package'], 'source_sha256': record['sha256'], 'sha256': hashlib.sha256(snippet).hexdigest(), 'syntax_index': index, 'name': unit['name'], 'kind': unit['kind'], 'range': span, 'body_range': unit['body_range'], 'start_line': source[:span[0]].count(b'\n') + 1, 'end_line': source[:span[1] - 1].count(b'\n') + 1, 'ancestors': unit['ancestors'], 'direct_doc_attributes': sum(attribute['path'] == 'doc' for attribute in unit['attributes']), 'direct_cfg_attributes': sum(attribute['path'] in {'cfg', 'cfg_attr'} for attribute in unit['attributes']), 'independent_test_eligible': False})
    dump(run / 'files.json', files)
    dump(run / 'units.json', units)
    summary = {'files': len(files), 'statuses': dict(Counter(file['status'] for file in files)), 'body_functions': len(units), 'unique_function_snippets': len({unit['sha256'] for unit in units}), 'functions_with_direct_doc': sum(unit['direct_doc_attributes'] > 0 for unit in units), 'functions_with_direct_cfg': sum(unit['direct_cfg_attributes'] > 0 for unit in units), 'failures': [file['path'] for file in files if file['status'] != 'parsed_by_syn'], 'unit_kinds': dict(sum((Counter(file['unit_kinds']) for file in files), Counter())), 'similarity_run': False, 'independent_test_units': 0}
    summary['artifacts_sha256'] = {str(path.relative_to(run)): sha(path) for path in sorted(run.rglob('*')) if path.is_file()}
    dump(run / 'report.json', summary)
    print(json.dumps({key: value for key, value in summary.items() if key != 'artifacts_sha256'}, indent=2))


if __name__ == '__main__':
    main()
