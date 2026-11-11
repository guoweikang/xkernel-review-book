"""Compare explicit exploratory models of call spellings, not resolved dependencies."""

import argparse
import hashlib
import json
from pathlib import Path

from run_reflexion_contract import project


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = json.loads((args.input / 'report.json').read_text())
    for name, expected in report['artifact_sha256'].items():
        assert hashlib.sha256((args.input / name).read_bytes()).hexdigest() == expected
    records = json.loads((args.input / 'calls.json').read_text())
    protocol = json.loads((args.input / 'protocol.json').read_text())
    strict = [('OF', 'cpu_view_spelling'), ('OF', 'local_reg_spelling'),
              ('OF', 'traversal_spelling'), ('DT', 'low_level_read'), ('DT', 'cpu_view_spelling')]
    models = {'strict_probe': strict, 'transitional_probe': strict + [('OF', 'low_level_read')]}
    results = []
    for label in ('before', 'after', 'current'):
        source_edges, rules, provenance = [], [], {}
        for record in records:
            if record['snapshot'] != label:
                continue
            caller = record['path'] + '::' + record['name']
            bucket = 'OF' if '/of/' in record['path'] else 'DT'
            rules.append({'source': caller, 'targets': [bucket]})
            for index, site in enumerate(record['sites']):
                identity = f'{caller}@{index}'
                source_edges.append((caller, identity))
                targets = [key for key, names in protocol['lexical_signals'].items()
                           if site['kind'] != 'opaque_macro' and site['name'] in names]
                if targets:
                    rules.append({'source': identity, 'targets': targets})
                provenance[identity] = {'path': record['path'], 'caller': record['name'],
                                        'source_sha256': record['source_sha256'], **site}
        for model, edges in models.items():
            result = project(edges, source_edges, rules, 'all')
            results.append({'snapshot': label, 'model': model, 'relation': 'contains_call_spelling',
                            'high_edges': edges, 'source_edges': source_edges, 'rules': rules,
                            'callsite_provenance': provenance, 'result': result})
    summary = {
        'kind': 'retrospective_model_sensitivity_not_accuracy_evaluation',
        'normative_status': 'analyst_hypotheses_not_approved_architecture_rules',
        'resolved_edges': 0, 'actual_violation_labels': None,
        'input_report_sha256': hashlib.sha256((args.input / 'report.json').read_bytes()).hexdigest(),
        'results': results,
    }
    for path in (Path(__file__), ROOT / 'scripts/run_reflexion_contract.py'):
        (args.output / path.name).write_bytes(path.read_bytes())
    summary['scripts_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in args.output.iterdir()}
    (args.output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    for result in results:
        projected = result['result']
        print(result['snapshot'], result['model'], 'divergence=', projected['divergence'],
              'source_sites=', len(result['source_edges']), 'unmapped=', len(projected['unmapped']))


if __name__ == '__main__':
    main()
