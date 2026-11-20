def validate_tree(output, source):
    assert output['source_text'] == source
    assert output['resolved_edges'] == 0 and output['cfg'] == 'not_evaluated'
    assert output['coverage']['domain'] == 'exported_body_subset_not_full_rust_ast'
    if output['status'] == 'rejected':
        assert not output['nodes'] and output['error']
        assert not output['coverage']['complete_supported']
        return
    nodes, scopes = output['nodes'], output['scopes']
    encoded = source.encode()
    incoming = [0] * len(nodes)
    for index, node in enumerate(nodes):
        assert node['node_id'] == index
        begin, end = node['range']
        assert 0 <= begin <= end <= len(encoded)
        assert encoded[begin:end].decode() == node['source_text']
        assert 0 <= node['scope_id'] < len(scopes)
        children = node['ordered_children']
        assert children == sorted(children, key=lambda child: (*nodes[child]['range'], child))
        for child in children:
            assert child > index and nodes[child]['parent_id'] == index
            assert begin <= nodes[child]['range'][0] <= nodes[child]['range'][1] <= end
            incoming[child] += 1
        assert node['coverage'] in ('supported', 'opaque')
        if node['coverage'] == 'opaque':
            assert node['reason'] and not children
        assert node['subtree_closed'] == (node['coverage'] == 'supported' and all(nodes[child]['subtree_closed'] for child in children))
    assert incoming[output['root_id']] == 0
    assert all(count == 1 for index, count in enumerate(incoming) if index != output['root_id'])
    assert output['coverage']['complete_supported'] == nodes[output['body_node_id']]['subtree_closed']
    assert output['coverage']['unsupported_nodes'] == sum(node['coverage'] == 'opaque' for node in nodes)
    for index, scope in enumerate(scopes):
        assert scope['scope_id'] == index
        assert scope['parent_id'] is None or 0 <= scope['parent_id'] < index
    for index, binder in enumerate(output['binders']):
        assert binder['binder_id'] == index
        assert nodes[binder['node_id']]['scope_id'] == binder['scope_id']
    for occurrence in output['occurrences']:
        node = nodes[occurrence['node_id']]
        assert node['source_text'] == occurrence['spelling']
        candidate = occurrence['binder_candidate']
        if candidate is not None:
            binder = output['binders'][candidate]
            assert occurrence['candidate_status'] == 'lexical_candidate'
            assert binder['normalized_name'] == occurrence['normalized_name']
            scope_chain = []
            scope = occurrence['scope_id']
            while scope is not None:
                scope_chain.append(scope)
                scope = scopes[scope]['parent_id']
            assert binder['scope_id'] in scope_chain
        if occurrence['role'] != 'local_use':
            assert candidate is None and occurrence['candidate_status'] == 'not_a_local_use'


def check_control(control, output):
    validate_tree(output, control['source'])
    if control['id'] == '12':
        assert output['status'] == 'rejected'
        return
    assert output['status'] == 'parsed'
    names = {'value', 'self', 'type', '值', 'result'}
    actual = []
    for occurrence in output['occurrences']:
        if occurrence['role'] == 'local_use' and occurrence['normalized_name'] in names:
            target = 'unknown' if occurrence['candidate_status'] == 'unknown_scope' else str(occurrence['binder_candidate'])
            actual.append(occurrence['normalized_name'] + ':' + target)
    assert actual == control['expected_local_uses'], (actual, control['expected_local_uses'])
    reasons = {node.get('reason') for node in output['nodes']}
    required = {
        '06': {'unsupported_qualified_or_generic_path'},
        '07': {'unsupported_closure'},
        '08': {'unsupported_let_pattern_attributes_or_else'},
        '09': {'unsupported_match', 'unsupported_for', 'unsupported_if_including_if_let'},
        '10': {'opaque_statement_macro', 'unsupported_let_pattern_attributes_or_else', 'unsupported_nested_item'},
        '11': {'opaque_statement_macro'},
    }
    assert required.get(control['id'], set()) <= reasons
    if control['id'] == '03':
        pairs = {(item['spelling'], item['role']) for item in output['occurrences']}
        assert {('touch', 'method_name'), ('field', 'field_name'), ('self', 'local_use')} <= pairs
    if control['id'] == '04':
        assert any(item['spelling'] == 'r#type' and item['normalized_name'] == 'type' for item in output['occurrences'])
