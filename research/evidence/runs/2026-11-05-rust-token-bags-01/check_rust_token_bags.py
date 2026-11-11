"""Constructed lexical checks; these do not establish detector accuracy."""

import argparse
from collections import Counter
from pathlib import Path

from prepare_rust_token_bags import decode_bag, encode_bag, tokenize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()

    def tokens(source):
        result = tokenize(args.binary.resolve(), source.encode())
        assert result['status'] == 'tokenized', result
        return result['tokens']

    plain = tokens('fn sample() { value(); }')
    assert plain == tokens('fn sample() { /* outer /* nested */ tail */ value(); // comment\n }')
    for literal in ['"https://host/*literal*/"', 'r##"// /* 中 */ @#@,@@::@@"##', "'中'", 'b\'x\'', '"\\\"quoted\\\""']:
        assert 'literal:' + literal in tokens('fn sample() { let value = ' + literal + '; }')
    lifetime = tokens("fn borrow<'scope>(value: &'scope str) -> &'scope str { value }")
    assert 'ident:scope' in lifetime and 'punct:\':joint' in lifetime
    assert 'ident:r#type' in tokens('fn sample(r#type: u8) { r#type; }')
    assert 'ident:数值' in tokens('fn sample(数值: u8) { 数值; }')
    assert tokens('fn sample() { left >>= right; }') != tokens('fn sample() { left > > = right; }')
    assert tokens('fn sample() { value(1); }') != tokens('fn sample() { value[1]; }')
    assert tokens('fn sample() { 1u32; }') != tokens('fn sample() { 1u64; }')
    assert 'ident:doc' in tokens('/// documentation\nfn sample() {}')
    assert tokenize(args.binary.resolve(), b'fn broken( {')['status'] == 'rejected'
    assert tokenize(args.binary.resolve(), b'"unterminated')['status'] == 'rejected'
    assert tokens('fn invalid() { let = ; }')
    special = ['literal:"@#@,@@::@@\n中文"', 'ident:r#type', 'literal:"@#@,@@::@@\n中文"']
    line = encode_bag(special, 1)
    assert decode_bag(line) == Counter(special)
    for corrupted in [line.replace('1,1,3,2,', '1,1,4,2,'), line + '0']:
        try:
            decode_bag(corrupted)
        except ValueError:
            continue
        raise AssertionError('Corrupt serialization accepted')
    print('PASS: nested comments; five literal forms; lifetimes; raw/Unicode identifiers; punctuation; delimiters; suffixes; doc desugaring; two lexical rejections; syntax-boundary control; reversible bags; two corruption rejections')


if __name__ == '__main__':
    main()
