"""Bind explicitly supplied call spellings to existing unresolved syntax evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def bind(binary, source, source_sha256, target):
    if hashlib.sha256(source).hexdigest() != source_sha256:
        raise ValueError('source identity mismatch')
    if not isinstance(target, str) or not target:
        raise ValueError('explicit target spelling required')
    result = subprocess.run([str(binary)], input=source, capture_output=True, check=True, timeout=20)
    parsed = json.loads(result.stdout)
    for site in parsed['sites']:
        start, end = site['range']
        if not 0 <= start < end <= len(source):
            raise ValueError('invalid byte span')
        site['source_text'] = source[start:end].decode('utf-8')
        assert site['target_resolution'] == 'unresolved'
        assert site['execution'] == 'not_established'
    matched = [site for site in parsed['sites'] if site['kind'] in ('call_expression', 'method_expression') and site['name'] == target]
    if parsed['status'] != 'parsed':
        state = 'parse_rejected'
    elif any(site['deferred_depth'] == 0 for site in matched):
        state = 'visible_spelling'
    elif matched:
        state = 'nested_spelling_only'
    else:
        state = 'no_visible_spelling'
    return {'state': state, 'matches': matched, 'syntax': parsed,
            'target_resolution': 'unknown', 'execution': 'unknown',
            'delegation_correctness': 'unknown', 'safe_exemption': 'unknown'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    protocol_path = ROOT / 'research/protocols/call-reference-binding-v1.json'
    plan = json.loads(protocol_path.read_text())
    inputs = ROOT / plan['input_run']
    prior = ROOT / plan['prior_probe_run']
    binary = ROOT / '.build/rust-call-probe/debug/rust-call-probe'
    old_report = json.loads((prior / 'report.json').read_text())
    assert sha(binary) == old_report['binary_sha256']
    assert sha(ROOT / 'research/tools/rust-syntax-probe/src/bin/rust-call-probe.rs') == sha(prior / 'probe.rs')
    manifest = json.loads((inputs / 'report.json').read_text())
    for name, digest in manifest['artifact_sha256'].items():
        assert sha(inputs / name) == digest
    cases = {case['id']: case for case in json.loads((inputs / 'cases.json').read_text())}
    references = {reference['id']: reference for reference in json.loads((inputs / 'references.json').read_text())}
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(protocol_path, args.output / 'protocol.json')
    shutil.copy2(__file__, args.output / 'runner.py')
    dump(args.output / 'freeze.json', {'protocol': sha(protocol_path), 'runner': sha(Path(__file__)),
        'input_manifest': sha(inputs / 'report.json'), 'binary': sha(binary), 'prior_report': sha(prior / 'report.json')})
    passes = []
    for repeat in (1, 2):
        records = []
        for claim in plan['claims']:
            reference = references[claim['case']]
            source = (inputs / reference['source_fragment']).read_bytes()
            identity = claim['case'] + '-' + claim['variant']
            text = cases[identity]['text']
            assert claim['target_spelling'] in text
            result = bind(binary, source, reference['unit']['sha256'], claim['target_spelling'])
            records.append({'id': identity, 'text': text, 'field_origin': plan['field_origin'],
                'unit_id': reference['unit']['id'], 'source_sha256': reference['unit']['sha256'],
                'source_fragment': reference['source_fragment'], 'target_spelling': claim['target_spelling'], **result})
        dump(args.output / f'bindings-{repeat}.json', records)
        passes.append(records)
    assert passes[0] == passes[1]
    controls = []
    for fixture in plan['controls']:
        source = fixture['source'].encode()
        result = bind(binary, source, hashlib.sha256(source).hexdigest(), fixture['target'])
        assert result['state'] == fixture['expected'], fixture['id']
        controls.append({**fixture, 'result': result})
    rejected = []
    source = b'fn probe() { self.target(); }'
    for label, digest, target in [('tamper', '0' * 64, 'target'), ('missing_target', hashlib.sha256(source).hexdigest(), '')]:
        try:
            bind(binary, source, digest, target)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(label)
    dump(args.output / 'controls.json', controls)
    report = {'claims': len(passes[0]), 'repeat_identical': True, 'controls_passed': len(controls),
        'invalid_inputs_rejected': rejected, 'states': {row['id']: row['state'] for row in passes[0]},
        'automated_natural_language_extraction': False, 'resolved_edges': 0, 'exemption_decisions': 0,
        'artifact_sha256': {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}}
    dump(args.output / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
