"""Replay syntax/projection evidence and reject a tampered artifact."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from run_reflexion_contract import project


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--syntax-run', type=Path, required=True)
    parser.add_argument('--projection-run', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.syntax_run / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((args.syntax_run / name).read_bytes()).hexdigest() == expected
    calls = json.loads((args.syntax_run / 'calls.json').read_text())
    assert report['units'] == len(calls) == 24
    assert report['resolved_edges'] == 0 and report['ownership_classifier'] is False
    for record in calls:
        fragment = record['fragment'].encode()
        assert hashlib.sha256(fragment).hexdigest() == record['fragment_sha256']
        for site in record['sites']:
            start, end = site['range']
            assert fragment[start:end].decode() == site['source_text']
            assert site['target_resolution'] == 'unresolved'
    projection = json.loads((args.projection_run / 'report.json').read_text())
    assert projection['actual_violation_labels'] is None
    for item in projection['results']:
        recomputed = project(item['high_edges'], item['source_edges'], item['rules'], 'all')
        assert json.loads(json.dumps(recomputed)) == item['result']
        for edge in item['result']['evidence']:
            for caller, callsite in edge['sources']:
                assert callsite in item['callsite_provenance']
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        syntax = temporary / 'syntax'
        subprocess.run([sys.executable, str(ROOT / 'scripts/probe_firmware_confirmation.py'),
                        '--output', str(syntax)], check=True, stdout=subprocess.DEVNULL)
        for name in ('calls.json', 'missing.json', 'controls.json', 'comparison.json'):
            assert (syntax / name).read_bytes() == (args.syntax_run / name).read_bytes()
        output = temporary / 'projection'
        command = [sys.executable, str(ROOT / 'scripts/project_firmware_syntax.py'),
                   '--input', str(syntax), '--output', str(output)]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        assert (output / 'report.json').read_bytes() == (args.projection_run / 'report.json').read_bytes()
        (syntax / 'calls.json').write_text('[]\n')
        bad = subprocess.run(command[:-1] + [str(temporary / 'tampered')],
                             capture_output=True)
        assert bad.returncode != 0
        assert not (temporary / 'tampered/report.json').exists()
    print('PASS: 24 fragment/site records; 7 controls replayed; 6 projections; repeat identity; tamper rejected')


if __name__ == '__main__':
    main()
