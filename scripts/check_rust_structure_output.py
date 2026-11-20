"""Independently validate native syntax-tree identities, spans and lexical links."""

import argparse
import json
from pathlib import Path


def check(source, payload):
    assert payload['source_text'].encode('utf-8') == source
    nodes_list = payload.get('nodes', [])
    if payload.get('status') == 'rejected':
        assert not nodes_list
        return {'status': 'rejected', 'nodes': 0, 'lexical_links': 0}
    assert payload['status'] == 'parsed'
    nodes = {node['node_id']: node for node in nodes_list}
    assert len(nodes) == len(nodes_list) and nodes
    scopes = {scope['scope_id']: scope for scope in payload['scopes']}
    binders = {binder['binder_id']: binder for binder in payload['binders']}
    assert len(scopes) == len(payload['scopes'])
    assert len(binders) == len(payload['binders'])
    roots = []
    for identity, node in nodes.items():
        start, end = node['range']
        assert 0 <= start < end <= len(source), (identity, node['range'])
        assert source[start:end].decode('utf-8') == node['source_text']
        assert node['scope_id'] in scopes
        children = node['ordered_children']
        assert len(set(children)) == len(children)
        assert children == sorted(children, key=lambda child: nodes[child]['range'][0])
        for child in children:
            assert nodes[child]['parent_id'] == identity
            assert start <= nodes[child]['range'][0] <= nodes[child]['range'][1] <= end
        parent = node['parent_id']
        if parent is None:
            roots.append(identity)
        else:
            assert identity in nodes[parent]['ordered_children']
        if node['coverage'] == 'opaque':
            assert node.get('reason') and not node['subtree_closed']
        else:
            assert node['coverage'] == 'supported'
    assert len(roots) == 1
    visited = set()

    def walk(identity):
        assert identity not in visited
        visited.add(identity)
        child_closed = [walk(child) for child in nodes[identity]['ordered_children']]
        closed = nodes[identity]['coverage'] == 'supported' and all(child_closed)
        assert nodes[identity]['subtree_closed'] == closed, identity
        return closed

    walk(roots[0])
    assert visited == set(nodes)
    assert payload['root_id'] == roots[0]
    assert payload['coverage']['complete_supported'] == nodes[payload['body_node_id']]['subtree_closed']
    assert payload['coverage']['exported_tree_closed'] == nodes[roots[0]]['subtree_closed']
    assert payload['coverage']['unsupported_nodes'] == sum(node['coverage'] == 'opaque' for node in nodes.values())
    assert payload['cfg'] == 'not_evaluated' and payload['resolved_edges'] == 0
    ancestry = {}
    for identity in scopes:
        ancestors = set()
        current = identity
        while current is not None:
            assert current in scopes and current not in ancestors
            ancestors.add(current)
            current = scopes[current]['parent_id']
        ancestry[identity] = ancestors
    for binder in binders.values():
        node = nodes[binder['node_id']]
        assert binder['scope_id'] in scopes
        assert node['scope_id'] == binder['scope_id']
        start, end = node['range']
        assert source[start:end].decode('utf-8') == binder['spelling']
        assert binder['normalized_name'] == binder['spelling'].removeprefix('r#')
    links = 0
    for occurrence in payload['occurrences']:
        node = nodes[occurrence['node_id']]
        start, end = node['range']
        assert source[start:end].decode('utf-8') == occurrence['spelling']
        assert occurrence['scope_id'] == node['scope_id']
        assert occurrence['normalized_name'] == occurrence['spelling'].removeprefix('r#')
        candidate = occurrence['binder_candidate']
        if occurrence['role'] in ('field_name', 'method_name', 'function_name'):
            assert candidate is None
        if occurrence['candidate_status'] == 'unknown_scope':
            assert candidate is None
        if candidate is not None:
            links += 1
            assert occurrence['candidate_status'] == 'lexical_candidate'
            binder = binders[candidate]
            assert binder['scope_id'] in ancestry[occurrence['scope_id']]
            assert binder['normalized_name'] == occurrence['normalized_name']
            assert nodes[binder['node_id']]['range'][1] <= start
    return {'status': payload['status'], 'nodes': len(nodes), 'lexical_links': links,
            'opaque_nodes': sum(node['coverage'] == 'opaque' for node in nodes.values()),
            'root_subtree_closed': nodes[roots[0]]['subtree_closed'],
            'semantic_binding_proven': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.source.read_bytes(), json.loads(args.output.read_text())), indent=2))


if __name__ == '__main__':
    main()
