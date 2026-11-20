"""Extract unresolved call spellings over the frozen common population."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ('syntax', 'fn demo() { let label = "中文"; library::call::<u8>(); object.read(); callback(); hidden!(secret()); }'),
    ('deferred', 'fn demo() { let task = || nested(); let future = async { later(); }; fn local() { inner(); } immediate(); }'),
    ('invalid', 'fn broken( {'),
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def frozen_path(info):
    path = ROOT / info['path']
    if digest(path.read_bytes()) != info['sha256']:
        raise ValueError('Frozen input changed: ' + info['path'])
    return path


def read_json(path):
    return json.loads(path.read_text())


def probe(binary, source, timeout, log):
    process = subprocess.run([str(binary)], input=source, capture_output=True, timeout=timeout)
    if process.stderr:
        log.write(process.stderr.decode('utf-8', errors='replace') + '\n')
    if process.returncode:
        raise ValueError(f'Probe exit {process.returncode}: {process.stdout!r}')
    result = json.loads(process.stdout)
    if result.get('schema') != 'rust-call-syntax/1' or result.get('status') not in {'parsed', 'rejected'}:
        raise ValueError('Unexpected probe response')
    if not isinstance(result.get('sites'), list):
        raise ValueError('Missing sites array')
    if result['status'] == 'rejected' and (result['sites'] or not result.get('error')):
        raise ValueError('Invalid rejected response')
    for site in result['sites']:
        start, end = site['range']
        if not 0 <= start < end <= len(source):
            raise ValueError('Call span outside source')
        site['source_text'] = source[start:end].decode('utf-8')
        if site['target_resolution'] != 'unresolved' or site['execution'] != 'not_established':
            raise ValueError('Syntax promoted to semantic fact')
        if site['cfg'] != 'not_evaluated':
            raise ValueError('Unexpected cfg interpretation')
        if site['kind'] not in {'call_expression', 'method_expression', 'opaque_macro'}:
            raise ValueError('Unknown site kind')
    return result


def validate_controls(controls):
    sites = controls['syntax']['sites']
    if [site['name'] for site in sites] != ['library::call', 'read', 'callback', 'hidden']:
        raise ValueError('Macro opacity or call classification regression')
    if sites[1]['source_text'] != 'read' or not sites[0]['source_text'].startswith('library::call'):
        raise ValueError('UTF-8 span regression')
    if sites[-1]['kind'] != 'opaque_macro':
        raise ValueError('Macro opacity lost')
    nested = controls['deferred']['sites']
    if {site['name']: site['deferred_depth'] for site in nested} != {
        'nested': 1, 'later': 1, 'inner': 1, 'immediate': 0,
    }:
        raise ValueError('Deferred/nested syntax regression')
    if controls['invalid']['status'] != 'rejected':
        raise ValueError('Invalid syntax was accepted')


def run(output):
    started = time.monotonic()
    protocol_path = output / 'protocol.json'
    if not protocol_path.is_file() or {path.name for path in output.iterdir()} != {'protocol.json'}:
        raise ValueError('Output must contain only the prewritten protocol.json')
    protocol = read_json(protocol_path)
    protocol_hash = digest(protocol_path.read_bytes())
    deadline = started + protocol['limits']['wall_seconds']
    scope = read_json(frozen_path(protocol['scope_protocol']))
    scope_units = read_json(frozen_path(protocol['scope_units']))
    corpus_report = read_json(frozen_path(protocol['corpus_report']))
    inputs = {name: frozen_path(info) for name, info in protocol['inputs'].items()}
    for name in ('units', 'tokens'):
        if protocol['inputs'][name] != scope['inputs'][name]:
            raise ValueError('Input is not anchored to common scope: ' + name)
    if corpus_report['revision'] != protocol['source_revision']:
        raise ValueError('Corpus revision mismatch')
    for name in ('units', 'unit_archive', 'source_archive'):
        path = inputs[name]
        if digest(path.read_bytes()) != corpus_report['artifacts_sha256'][path.name]:
            raise ValueError('Corpus archive identity mismatch')
    probe_inputs = {name: frozen_path(info) for name, info in protocol['probe'].items()}
    prior = read_json(probe_inputs['prior_report'])
    if digest(probe_inputs['binary'].read_bytes()) != prior['binary_sha256']:
        raise ValueError('Binary differs from original probe')
    if digest(probe_inputs['source'].read_bytes()) != prior['artifact_sha256']['probe.rs']:
        raise ValueError('Rust frontend changed')
    units_list = read_json(inputs['units'])
    units = {unit['id']: unit for unit in units_list}
    if len(units) != len(units_list):
        raise ValueError('Duplicate source IDs')
    token_rows = read_json(inputs['tokens'])['records']
    selected = sorted(row['unit_id'] for row in token_rows if row.get('size_eligible'))
    scope_selected = {row['unit_id'] for row in scope_units if row['code_eligible']}
    if len(selected) != protocol['expected_units'] or len(set(selected)) != len(selected):
        raise ValueError('Population denominator mismatch')
    if set(selected) != scope_selected or not set(selected) <= set(units):
        raise ValueError('Common population IDs differ')
    shutil.copyfile(__file__, output / 'runner.py')
    for key, name in [('source', 'probe.rs'), ('cargo_toml', 'Cargo.toml'), ('cargo_lock', 'Cargo.lock')]:
        shutil.copyfile(probe_inputs[key], output / name)
    dump(output / 'environment.json', {
        'python': sys.version, 'python_executable': sys.executable,
        'platform': platform.platform(), 'command': sys.argv, 'cwd': str(Path.cwd()),
        'binary_path': str(probe_inputs['binary']),
        'binary_sha256': digest(probe_inputs['binary'].read_bytes()),
        'binary_provenance': 'Byte-identical to frozen reviewed-call-syntax binary; not rebuilt',
        'build_toolchain_this_run': 'not_run', 'network_installation': False,
        'frontend_sha256': digest(probe_inputs['source'].read_bytes()),
        'runner_sha256': digest(Path(__file__).read_bytes()), 'protocol_sha256': protocol_hash,
    })
    records = []
    controls = {}
    control_error = None
    deadline_exceeded = False
    with (output / 'run.log').open('w') as log:
        log.write(f'Frozen population: {len(selected)}; protocol: {protocol_hash}\n')
        try:
            for name, text in FIXTURES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Batch wall budget exhausted in controls')
                controls[name] = probe(probe_inputs['binary'], text.encode(),
                                       min(protocol['limits']['per_probe_seconds'], remaining), log)
            validate_controls(controls)
        except Exception as error:
            control_error = f'{type(error).__name__}: {error}'
            log.write('CONTROL_FAILURE ' + control_error + '\n')
        dump(output / 'controls.json', {
            'inputs': FIXTURES, 'results': controls,
            'passed': control_error is None, 'error': control_error,
        })
        with zipfile.ZipFile(inputs['unit_archive']) as snippets, \
                zipfile.ZipFile(inputs['source_archive']) as source_files, \
                zipfile.ZipFile(output / 'selected-units.zip', 'w', zipfile.ZIP_DEFLATED) as saved:
            for identity in selected:
                unit = units[identity]
                record = {
                    'unit_id': identity, 'path': unit['path'], 'name': unit['name'],
                    'kind': unit['kind'], 'entry': unit['entry'], 'range': unit['range'],
                    'original_range': unit['original_range'],
                    'source_sha256': unit['sha256'], 'file_source_sha256': unit['source_sha256'],
                    'source_text': None, 'schema': 'rust-call-syntax/1',
                    'status': 'adapter_error', 'sites': [],
                }
                try:
                    source = snippets.read(unit['entry'])
                    whole = source_files.read(unit['path'])
                    start, end = unit['range']
                    if digest(source) != unit['sha256'] or digest(whole) != unit['source_sha256']:
                        raise ValueError('Source identity mismatch')
                    if source != whole[start:end]:
                        raise ValueError('Source slice mismatch')
                    record['source_text'] = source.decode('utf-8')
                    saved.writestr(unit['entry'], source)
                    remaining = deadline - time.monotonic()
                    if control_error:
                        record.update(status='not_run_due_to_gate', error=control_error)
                    elif remaining <= 0:
                        deadline_exceeded = True
                        record.update(status='not_run_due_to_deadline', error='Batch wall budget exhausted')
                    else:
                        record.update(probe(probe_inputs['binary'], source,
                                            min(protocol['limits']['per_probe_seconds'], remaining), log))
                except Exception as error:
                    record.update(status='adapter_error', sites=[], error=f'{type(error).__name__}: {error}')
                records.append(record)
                log.write(json.dumps({'unit_id': identity, 'status': record['status'],
                                      'sites': len(record['sites']), 'error': record.get('error')}) + '\n')
        log.write(f'Completed records: {len(records)}; elapsed: {time.monotonic() - started:.3f}s\n')
    if len(records) != len(selected) or {row['unit_id'] for row in records} != set(selected):
        raise ValueError('Extraction dropped population members')
    dump(output / 'calls.json', {
        'schema': 'common-call-syntax/1', 'source_revision': protocol['source_revision'],
        'protocol_sha256': protocol_hash, 'resolved_edges': 0, 'records': records,
    })
    sites = [site for record in records for site in record['sites']]
    failures = [row['unit_id'] for row in records if row['status'] != 'parsed']
    if digest(protocol_path.read_bytes()) != protocol_hash:
        raise ValueError('Protocol changed during execution')
    summary = {
        'schema': 'common-call-syntax-summary/1', 'population': len(selected),
        'records': len(records), 'status_counts': dict(Counter(row['status'] for row in records)),
        'failed_or_unexecuted_unit_ids': failures,
        'zero_site_parsed_units': sum(row['status'] == 'parsed' and not row['sites'] for row in records),
        'sites': len(sites), 'site_kinds': dict(Counter(site['kind'] for site in sites)),
        'deferred_sites': sum(site['deferred_depth'] > 0 for site in sites),
        'null_name_sites': sum(site['name'] is None for site in sites),
        'resolved_edges': 0, 'controls_passed': control_error is None,
        'deadline_exceeded': deadline_exceeded, 'elapsed_seconds': time.monotonic() - started,
        'passed': not failures and control_error is None,
        'model_runs': 0, 'ranking': 'not_run', 'frontend_modified': False,
        'limits': [
            'Syntactic spellings are not resolved API or callee identities.',
            'No type checking, cfg evaluation, macro expansion or runtime evidence.',
            'deferred_depth and source ordering do not establish execution order.',
            'No-site parsed rows differ from rejected or unexecuted rows.',
            '812 is the fixed token-length eligible subset, not the full 2180-unit corpus.',
        ],
        'artifact_sha256': {path.name: digest(path.read_bytes())
                            for path in sorted(output.iterdir()) if path.is_file()},
    }
    dump(output / 'summary.json', summary)
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in {'artifact_sha256', 'limits', 'failed_or_unexecuted_unit_ids'}}))
    return 0 if summary['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    return run(args.output.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
