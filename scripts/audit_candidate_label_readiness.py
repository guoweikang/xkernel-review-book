"""Audit existing development materials without manufacturing truth labels."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    run_id = sys.argv[1]
    assert run_id and all(character.isalnum() or character in '-_' for character in run_id)
    output = ROOT / 'research/evidence/runs' / run_id
    output.mkdir()
    names = ['discovery-ledger-v4', 'doc-tfidf-review-v1', 'firmware-confirmation-v1', 'layered-candidate-evaluation-v1']
    inputs = {name: ROOT / f'research/protocols/{name}.json' for name in names}
    frozen = list(inputs.values()) + [Path(__file__), ROOT / 'scripts/evaluate_layered_candidates.py', ROOT / 'scripts/check_layered_candidate_evaluation.py']
    manifest = {'scope': 'material-readiness audit and evaluator controls; no new semantic labels or effectiveness result',
                'sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in frozen}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    data = {name: json.loads(path.read_text()) for name, path in inputs.items()}
    ledger = data['discovery-ledger-v4']
    records = ledger['records']
    keys = [tuple(sorted(record['file_ids'])) for record in records]
    assert len(keys) == len(set(keys)) == ledger['summary']['candidate_pairs']
    labels = Counter('unlabelled' if record['truth_label'] is None else str(record['truth_label']) for record in records)
    reviews = Counter(record['review_status'] for record in records)
    assert reviews['reviewed'] == ledger['summary']['reviewed_pairs']
    families = ledger['families']
    missing = []
    for family in families:
        for evidence in family['evidence']:
            if not (ROOT / evidence).exists():
                missing.append(evidence)
    assert not missing, missing
    controls = subprocess.run([sys.executable, 'scripts/check_layered_candidate_evaluation.py'], cwd=ROOT,
                              capture_output=True, text=True, timeout=30)
    (output / 'controls.stdout').write_text(controls.stdout)
    (output / 'controls.stderr').write_text(controls.stderr)
    controls.check_returncode()
    report = {'scc': {'candidate_pairs': len(records), 'labels': dict(labels), 'review_status': dict(reviews),
                      'assigned_families': len(families), 'family_truth_labels': dict(Counter('unlabelled' if family['truth_label'] is None else str(family['truth_label']) for family in families)),
                      'source_identity_bound_records': sum(len(record['members']) == 2 and all(member.get('id') and member.get('path') and member.get('start_line') for member in record['members']) for record in records),
                      'independent_effectiveness_eligible': False},
              'documentation': {'reviewed_records': len(data['doc-tfidf-review-v1']['records']),
                                'scope': data['doc-tfidf-review-v1']['scope'],
                                'independent_effectiveness_eligible': False},
              'firmware': {'syntax_controls': len(data['firmware-confirmation-v1']['controls']),
                           'independent_responsibility_labels': 0},
              'limits': ['No effective precision or recall calculated', 'No declaration that standard Rust libraries provide labels',
                         'No full benchmark downloaded or run', 'Source identity presence does not establish config completeness'],
              'next': ['Bind source/config and family lineage for development hard cases',
                       'Separate observer-independent relation labels from merge benefit',
                       'Collect independent adjudication before effectiveness comparison']}
    (output / 'readiness.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
