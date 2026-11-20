"""Controls for discovery population matching and missing-input preservation."""

import copy

from audit_discovery_scope import align


def main():
    unit = {'id': 'one', 'path': 'src.rs', 'package': 'crate', 'range': [0, 100],
            'start_line': 1, 'test_path_hint': False, 'cfg': 'not_evaluated'}
    token = {'unit_id': 'one', 'path': 'src.rs', 'range': [0, 100], 'status': 'tokenized',
             'tokens': 65, 'size_eligible': True}
    doc = {'unit_id': 'one', 'path': 'src.rs', 'package': 'crate', 'doc_text': ''}
    pattern = r'(?u)\b\w\w+\b'
    assert align([unit], [token], [doc], pattern)[0]['doc_state'] == 'missing_or_empty'
    assert align([unit], [token], [doc | {'doc_text': 'x'}], pattern)[0]['doc_state'] == 'tokenizer_zero'
    assert align([unit], [token], [doc | {'doc_text': 'buffer'}], pattern)[0]['doc_state'] == 'nonzero'
    assert not align([unit], [token | {'tokens': 64, 'size_eligible': False}], [doc], pattern)[0]['code_eligible']
    invalid = [([unit, unit], [token], [doc]), ([unit], [token], []),
               ([unit], [token], [doc | {'path': 'wrong.rs'}]),
               ([unit], [token | {'size_eligible': False}], [doc]),
               ([unit], [token | {'range': [1, 100]}], [doc])]
    for units, tokens, docs in copy.deepcopy(invalid):
        try:
            align(units, tokens, docs, pattern)
        except ValueError:
            continue
        raise AssertionError('Invalid identity/eligibility accepted')
    print('PASS: 4 positive boundary controls, 5 invalid input controls')


if __name__ == '__main__':
    main()
