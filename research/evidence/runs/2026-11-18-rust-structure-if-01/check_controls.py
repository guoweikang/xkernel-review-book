import importlib.util
import pathlib

REFERENCE = pathlib.Path(__file__).resolve().parent.parent / '2026-11-18-rust-structure-prototype-01/check_controls.py'
SPEC = importlib.util.spec_from_file_location('baseline_structure_checks', REFERENCE)
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)
validate_tree = BASELINE.validate_tree


def check_control(control, output):
    if int(control['id']) <= 12:
        BASELINE.check_control(control, output)
        return
    validate_tree(output, control['source'])
    assert output['status'] == 'parsed'
    uses = [item for item in output['occurrences'] if item['role'] == 'local_use' and item['normalized_name'] == 'value']
    actual = ['value:' + ('unknown' if item['candidate_status'] == 'unknown_scope' else str(item['binder_candidate'])) for item in uses]
    assert actual == control['expected_local_uses'], (actual, control['expected_local_uses'])
    nodes = output['nodes']
    branches = [node for node in nodes if node['syntax_kind'] == 'ordinary_if']
    assert len(branches) == control['expected_if_nodes']
    for branch in branches:
        children = [nodes[child] for child in branch['ordered_children']]
        assert [child['role'] for child in children] == ['condition', 'then_branch', 'else_branch']
        then = children[1]
        assert then['syntax_kind'] == 'block'
        assert then['scope_id'] != branch['scope_id']
        assert output['scopes'][then['scope_id']]['parent_id'] == branch['scope_id']
        otherwise = children[2]
        if otherwise['syntax_kind'] == 'block_expression':
            block = nodes[otherwise['ordered_children'][0]]
            assert block['scope_id'] != then['scope_id']
            assert output['scopes'][block['scope_id']]['parent_id'] == branch['scope_id']
        else:
            assert otherwise['syntax_kind'] == 'ordinary_if'
    if control['id'] == '15':
        assert sum(node.get('reason') == 'unsupported_if_including_if_let' for node in nodes) == 2
        assert not output['coverage']['complete_supported']
    if control['id'] == '16':
        assert all(item['binder_candidate'] is None for item in uses)
        assert any(node.get('reason') == 'opaque_statement_macro' for node in nodes)
        assert not output['coverage']['lexical_scopes_without_unknown_effects']
        assert not output['coverage']['complete_supported']
    if control['id'] in ('13', '14'):
        assert output['coverage']['complete_supported']
