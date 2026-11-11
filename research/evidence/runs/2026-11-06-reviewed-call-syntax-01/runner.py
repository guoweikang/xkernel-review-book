"""Extract unresolved call syntax from fixed reviewed units; never emit resolved call edges."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    binary = ROOT / '.build/rust-call-probe/debug/rust-call-probe'
    corpus = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'
    report = json.loads((corpus / 'report.json').read_text())
    for name in ['units.json', 'units.zip', 'sources.zip']:
        if hashlib.sha256((corpus / name).read_bytes()).hexdigest() != report['artifacts_sha256'][name]:
            raise ValueError('Corpus identity changed')
    ledger_path = ROOT / 'research/protocols/discovery-ledger-v4.json'
    ledger = json.loads(ledger_path.read_text())
    members = {member['id']: member for pair in ledger['records'] if pair['review_status'] == 'reviewed'
               for member in pair['members']}
    units = {unit['id']: unit for unit in json.loads((corpus / 'units.json').read_text())}

    def probe(source):
        result = subprocess.run([str(binary)], input=source, capture_output=True, check=True)
        parsed = json.loads(result.stdout)
        for site in parsed['sites']:
            start, end = site['range']
            if not 0 <= start < end <= len(source):
                raise ValueError('Call span outside source')
            site['source_text'] = source[start:end].decode('utf-8')
            if site['target_resolution'] != 'unresolved' or site['execution'] != 'not_established':
                raise ValueError('Syntax promoted to semantic fact')
        return parsed

    fixtures = [
        ('syntax', 'fn demo() { let label = "中文"; library::call::<u8>(); object.read(); callback(); hidden!(secret()); }'),
        ('deferred', 'fn demo() { let task = || nested(); let future = async { later(); }; fn local() { inner(); } immediate(); }'),
        ('invalid', 'fn broken( {'),
    ]
    controls = {name: probe(source.encode()) for name, source in fixtures}
    sites = controls['syntax']['sites']
    if [site['name'] for site in sites] != ['library::call', 'read', 'callback', 'hidden']:
        raise ValueError('Macro opacity or call classification regression')
    if sites[1]['source_text'] != 'read' or not sites[0]['source_text'].startswith('library::call'):
        raise ValueError('UTF-8 span regression')
    nested = controls['deferred']['sites']
    if {site['name']: site['deferred_depth'] for site in nested} != {'nested': 1, 'later': 1, 'inner': 1, 'immediate': 0}:
        raise ValueError('Deferred/nested syntax regression')
    if controls['invalid']['status'] != 'rejected':
        raise ValueError('Invalid syntax was accepted')
    records = []
    with zipfile.ZipFile(corpus / 'units.zip') as archive:
        for identity in sorted(members):
            unit = units[identity]
            source = archive.read(unit['entry'])
            if hashlib.sha256(source).hexdigest() != unit['sha256']:
                raise ValueError('Unit identity differs')
            parsed = probe(source)
            records.append({'unit_id': identity, 'path': unit['path'], 'name': unit['name'],
                            'source_sha256': unit['sha256'], 'original_range': unit['original_range'], **parsed})
    (args.output / 'calls.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    (args.output / 'controls.json').write_text(json.dumps({'inputs': fixtures, 'results': controls}, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(__file__, args.output / 'runner.py')
    shutil.copyfile(ROOT / 'research/tools/rust-syntax-probe/src/bin/rust-call-probe.rs', args.output / 'probe.rs')
    for name in ['Cargo.toml', 'Cargo.lock']:
        shutil.copyfile(ROOT / 'research/tools/rust-syntax-probe' / name, args.output / name)
    sites = [site for record in records for site in record['sites']]
    summary = {'schema': 'reviewed-call-syntax/1', 'reviewed_pairs': 18, 'unique_units': len(records),
               'unit_status': dict(Counter(record['status'] for record in records)),
               'site_kinds': dict(Counter(site['kind'] for site in sites)),
               'deferred_sites': sum(site['deferred_depth'] > 0 for site in sites),
               'resolved_edges': 0, 'retrieval_comparison': 'not_run',
               'ledger_sha256': hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
               'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'limitations': ['Syntactic calls include function-pointer variables, constructors and unresolved associated paths',
                              'No types, cfg evaluation, macro expansion, implicit drops or execution/path proof',
                              'deferred_depth marks closure/async/item nesting, not actual runtime timing',
                              'Names and source spans are retrieval hints, not callee identity'],
               'artifact_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in args.output.iterdir() if path.is_file()}}
    (args.output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key not in {'artifact_sha256', 'limitations'}}, indent=2))


if __name__ == '__main__':
    main()
