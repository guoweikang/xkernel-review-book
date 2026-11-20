"""Bounded source-to-norm traceability audit, not an architecture detector."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def conditional_status(owner, exception):
    if owner not in ('DT', 'OF') or exception not in ('absent', 'unknown', 'established'):
        raise ValueError('Unsupported explicit premise')
    if owner == 'OF':
        return 'permitted_under_counterfactual'
    if exception == 'unknown':
        return 'exception_applicability_unknown'
    if exception == 'established':
        return 'exempt_under_explicit_condition'
    return 'candidate_under_assumption'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    protocol_path = ROOT / 'research/protocols/firmware-conditional-location-v1.json'
    protocol = json.loads(protocol_path.read_text())
    source_input = ROOT / protocol['source_input']
    shutil.copyfile(protocol_path, output / 'protocol.json')
    shutil.copyfile(__file__, output / 'auditor.py')
    (output / 'freeze.json').write_text(json.dumps({
        'protocol_sha256': sha(protocol_path.read_bytes()),
        'source_input_sha256': sha(source_input.read_bytes()),
        'auditor_sha256': sha(Path(__file__).read_bytes())}, indent=2) + '\n')
    matches = [row for row in json.loads(source_input.read_text())
               if row['snapshot'] == protocol['snapshot'] and row['name'] == protocol['function']
               and row['path'] == protocol['path']]
    assert len(matches) == 1
    fact = matches[0]
    assert fact['commit'] == protocol['revision']
    def original(path):
        return subprocess.check_output(['git', '-C', '/root/codes/x-kernel', 'show',
                                        protocol['revision'] + ':' + path], timeout=30)
    source = original(protocol['path'])
    document = original(protocol['norm_document'])
    assert sha(source) == fact['source_sha256']
    start, end = fact['range']
    assert source[start:end].decode() == fact['fragment']
    sites = [site for site in fact['sites'] if site['name'] == protocol['site_name']]
    assert len(sites) == 1
    site = sites[0]
    first, last = site['file_range']
    assert source[first:last].decode() == site['source_text']
    assert site['line'] == source[:first].count(b'\n') + 1
    records = []
    for condition in protocol['conditions']:
        interval = condition['document_lines']
        excerpt = '\n'.join(document.decode().splitlines()[interval[0]-1:interval[1]]) if interval else None
        records.append({'condition': condition, 'source_site': site,
                        'source_line': source.decode().splitlines()[site['line']-1],
                        'norm_excerpt': excerpt,
                        'result': conditional_status(condition['owner'], condition['exception_condition']),
                        'actual_violation': 'unknown', 'provider_approval': 'unverified',
                        'semantic_role_mapping': 'analyst_hypothesis_not_resolved',
                        'why_document_matters': 'Owner assignment and migration qualification are not derivable from implementation location alone.'})
    assert conditional_status('DT', 'unknown') not in ('candidate_under_assumption', 'exempt_under_explicit_condition')
    assert conditional_status('DT', 'established') == 'exempt_under_explicit_condition'
    try:
        conditional_status('invented', 'absent')
    except ValueError:
        pass
    else:
        raise AssertionError('Undeclared owner accepted')
    result = {'source_sha256': sha(source), 'document_sha256': sha(document), 'fact': fact,
              'records': records, 'source_range_verified': True,
              'new_accuracy_measurement': False, 'new_kernel_execution': False,
              'limits': 'Known development candidate; premise propagation and source identity only, not automatic norm extraction or confirmed responsibility violations.'}
    (output / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('PASS: same verified source location x 3 explicit premises; unknown exception preserved; actual violations all unknown')


if __name__ == '__main__':
    main()
