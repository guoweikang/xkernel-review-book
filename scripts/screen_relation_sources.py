"""Record a bounded static screen of previously frozen external source files."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS = {
    'examples/vsock_server/src/main.rs': ('defer', 'Host example; not a selected implementation-pair task.'),
    'src/device/net/mod.rs': ('context', 'Header types and conversion; inspect only if a typed mechanism candidate needs it.'),
    'src/device/virtio_9p.rs': ('retain', 'read_mount_tag delegates consistency retries to Transport::read_consistent.'),
    'src/transport/mod.rs': ('retain', 'Generic consistency helper and u8/u16 adapters to u32 conversion; existing reuse controls.'),
    'src/tee_api_types.rs': ('context', 'ABI types/default/formatting; not an independent duplicate-engine label.'),
    'src/bin/log_test.rs': ('defer', 'Small logging executable; no implementation-pair hypothesis selected.'),
    'src/user_ta_header.rs': ('retain', 'bit delegates to bit32; width-specific helpers require explicit domain/type mapping.'),
    'tests/test_tee_api_arith_mpi.rs': ('defer', 'Arithmetic tests; test repetition is a separate task, not discarded as worthless.'),
    'tests/cases/tests/dns_resolver_recvmsg.rs': ('defer', 'Guest integration regression, not independent production mechanism.'),
    'tests/host-companions/vsock-perf-client/src/utils.rs': ('context', 'Timing/rate helpers; no selected duplicate implementation partner.'),
    'src/scheduler.rs': ('retain', 'Barrier delegates to complement of eligibility; resource-policy evidence needed for changes.'),
    'framework-tests/rust/guest_disk.rs': ('defer', 'Harness regression tests; retain as context, no production duplication label.'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'research/evidence/runs/2026-11-16-relation-validation-01/source-inventory.json'
    shutil.copyfile(source, args.output / 'source-inventory.json')
    shutil.copyfile(__file__, args.output / 'screen.py')
    rows = []
    provenance = []
    for repo in json.loads(source.read_text()):
        indexed = {item['path']: item for item in repo['files']}
        for name in repo['selected_paths']:
            content = subprocess.check_output(['git', '-C', repo['repository'], 'show', repo['revision'] + ':' + name], timeout=30)
            assert sha(content) == indexed[name]['sha256']
            decision, reason = DISPOSITIONS[name]
            lines = content.decode().splitlines()
            rows.append({'repository': repo['repository'], 'revision': repo['revision'], 'path': name,
                         'sha256': sha(content), 'line_count': len(lines), 'disposition': decision, 'reason': reason,
                         'read_scope': 'Signature/header screen for all; targeted bodies for retained candidates, not exhaustive code review.',
                         'review_basis': 'single-researcher-static', 'independent_test_eligible': False,
                         'source_claim_lines': [{'line': number, 'text': line} for number, line in enumerate(lines, 1)
                                                if 'SPDX-License-Identifier' in line or 'translation of OP-TEE' in line]})
        for name in ('Cargo.toml', 'README.md'):
            content = subprocess.check_output(['git', '-C', repo['repository'], 'show', repo['revision'] + ':' + name], timeout=30)
            relevant = [{'line': number, 'text': line} for number, line in enumerate(content.decode().splitlines(), 1)
                        if any(term in line.lower() for term in ('x-kernel', 'xkernel', 'rcore-os', 'license', 'repository'))]
            provenance.append({'repository': repo['repository'], 'revision': repo['revision'], 'path': name,
                               'sha256': sha(content), 'source_claims': relevant,
                               'limits': 'Repository self-description, not complete ancestry or license audit.'})
    assert len(rows) == len(DISPOSITIONS) == 12
    report = {'inventory_sha256': sha(source.read_bytes()), 'rows': rows, 'provenance': provenance,
              'new_executions': 0, 'independent_cases': 0,
              'limits': 'After frozen sampling, static triage; not pre-registered effectiveness or semantic truth.'}
    (args.output / 'screening.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print({decision: sum(row['disposition'] == decision for row in rows) for decision in ('retain', 'context', 'defer')})


if __name__ == '__main__':
    main()
