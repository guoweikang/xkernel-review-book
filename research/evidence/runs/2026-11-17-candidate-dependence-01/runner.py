import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def keys(case, level):
    result = set()
    for member in case['members']:
        result.add(('unit', member['id']))
        if level in ('exact_body', 'source_file'):
            result.add(('snippet', member['sha256']))
        if level == 'source_file':
            result.add(('source', member['path'], member['source_sha256']))
    return result


def group(cases, level):
    identities = [case['case_id'] for case in cases]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate case ID')
    owners = {identity: identity for identity in identities}

    def root(identity):
        while owners[identity] != identity:
            identity = owners[identity]
        return identity

    features = {case['case_id']: keys(case, level) for case in cases}
    edges = []
    for left, right in itertools.combinations(sorted(identities), 2):
        shared = features[left] & features[right]
        if shared:
            edges.append({'left': left, 'right': right, 'reasons': sorted(shared)})
            owners[root(right)] = root(left)
    groups = {}
    for identity in sorted(identities):
        groups.setdefault(root(identity), []).append(identity)
    return {'components': sorted(groups.values()), 'edges': edges}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    run.mkdir(exist_ok=False)
    protocol_path = ROOT / 'research/protocols/candidate-dependence-audit-v1.json'
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / 'research/evidence/runs' / protocol['parent']
    parent_report = json.loads((parent / 'report.json').read_text())
    for name, expected in parent_report['artifacts_sha256'].items():
        assert sha(parent / name) == expected, name
    historical = ROOT / 'research/evidence/runs' / protocol['historical_queue'] / 'review-queue.json'
    for origin, name in ((protocol_path, 'protocol.json'), (Path(__file__), 'runner.py'), (parent / 'reviewer/cases.json', 'cases.json'), (historical, 'historical-queue.json')):
        shutil.copyfile(origin, run / name)
    dump(run / 'freeze.json', {path.name: sha(path) for path in run.iterdir() if path.is_file()})
    cases = json.loads((run / 'cases.json').read_text())
    old = json.loads((run / 'historical-queue.json').read_text())
    old_pairs = {tuple(sorted(row['unit_ids'])) for row in old}
    old_endpoints = {identity for pair in old_pairs for identity in pair}
    old_paths = {member['path'] for row in old for member in row['members']}
    novelty = []
    for case in cases:
        pair = tuple(sorted(member['id'] for member in case['members']))
        novelty.append({'case_id': case['case_id'], 'pair_previously_in_queue': pair in old_pairs, 'old_endpoints': sum(member['id'] in old_endpoints for member in case['members']), 'old_source_paths': sum(member['path'] in old_paths for member in case['members'])})
    graphs = {level: group(cases, level) for level in protocol['graphs']}
    dump(run / 'graphs.json', graphs)
    dump(run / 'exposure.json', novelty)
    report = {
        'cases': len(cases),
        'unique_endpoints': len({member['id'] for case in cases for member in case['members']}),
        'unique_source_files': len({(member['path'], member['source_sha256']) for case in cases for member in case['members']}),
        'packages': sorted({member['package'] for case in cases for member in case['members']}),
        'graphs': {level: {'components': len(graph['components']), 'sizes': sorted([len(component) for component in graph['components']], reverse=True), 'edges': len(graph['edges'])} for level, graph in graphs.items()},
        'old_pairs': sum(row['pair_previously_in_queue'] for row in novelty),
        'new_pairs': [row for row in novelty if not row['pair_previously_in_queue']],
        'independent_test_cases_certified': 0,
    }
    report['artifacts_sha256'] = {path.name: sha(path) for path in sorted(run.iterdir()) if path.is_file()}
    dump(run / 'report.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'artifacts_sha256'}, indent=2))


if __name__ == '__main__':
    main()
