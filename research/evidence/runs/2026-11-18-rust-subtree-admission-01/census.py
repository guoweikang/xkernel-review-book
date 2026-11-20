import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / '2026-11-18-rust-structure-prototype-01/corpus'
KINDS = {'call', 'method_call', 'binary', 'unary', 'assign', 'reference',
         'field', 'index', 'tuple', 'array', 'return', 'block_expression', 'let'}


def measure():
    rows = []
    inputs = sorted(INPUT.glob('*.stdout'))
    assert len(inputs) == 8
    for path in inputs:
        payload = json.loads(path.read_text())
        nodes = {node['node_id']: node for node in payload['nodes']}

        def descendants(identity):
            return {identity}.union(*(descendants(child) for child in nodes[identity]['ordered_children']))

        body_nodes = descendants(payload['body_node_id'])
        eligible = {identity for identity in body_nodes
                    if nodes[identity]['syntax_kind'] in KINDS
                    and nodes[identity]['subtree_closed']
                    and len(descendants(identity)) >= 3}
        selected = []
        for identity in sorted(eligible):
            ancestor = nodes[identity]['parent_id']
            ancestors = set()
            while ancestor is not None:
                ancestors.add(ancestor)
                ancestor = nodes[ancestor]['parent_id']
            if ancestors & eligible:
                continue
            members = descendants(identity)
            uses = [occurrence for occurrence in payload['occurrences']
                    if occurrence['node_id'] in members and occurrence['role'] == 'local_use']
            candidates = collections.Counter(occurrence['binder_candidate'] for occurrence in uses
                                             if occurrence['binder_candidate'] is not None)
            selected.append({'node_id': identity, 'range': nodes[identity]['range'],
                             'kind': nodes[identity]['syntax_kind'], 'nodes': len(members),
                             'local_use_statuses': dict(collections.Counter(occurrence['candidate_status'] for occurrence in uses)),
                             'repeated_candidate_groups': sum(count >= 2 for count in candidates.values()),
                             'source_text': nodes[identity]['source_text']})
        rows.append({'unit_id': path.stem, 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'body_closed': payload['coverage']['complete_supported'], 'subtrees': selected})
    return {'units': rows, 'unit_count': len(rows),
            'units_with_subtrees': sum(bool(row['subtrees']) for row in rows),
            'subtrees': sum(len(row['subtrees']) for row in rows),
            'units_with_repeated_candidate_groups': sum(any(tree['repeated_candidate_groups'] for tree in row['subtrees']) for row in rows),
            'protocol_sha256': hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest(),
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    assert not (HERE / 'results.json').exists(), 'Refusing overwrite'
    first = measure()
    second = measure()
    assert first == second
    (HERE / 'results.json').write_text(json.dumps(first, indent=2) + '\n')
    (HERE / 'repeat.json').write_text(json.dumps({'equal': first == second, 'independent_measurements': False}) + '\n')
    print(json.dumps({key: value for key, value in first.items() if key != 'units'}))
