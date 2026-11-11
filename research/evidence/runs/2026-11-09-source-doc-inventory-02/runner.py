"""Bind literal documentation to fixed source objects; no cfg or macro evaluation."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'research/evidence/runs/2026-11-05-rust-baseline-corpus-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(binary, source):
    result = json.loads(subprocess.run(
        [str(binary)], input=source, capture_output=True, check=True, timeout=30).stdout)
    if result['status'] != 'parsed_by_syn':
        raise ValueError(f"Source rejected: {result['status']}")
    for owner in [dict(attributes=result['file_attributes']), *result['units']]:
        for attribute in owner['attributes']:
            start, end = attribute['range']
            if not 0 <= start < end <= len(source):
                raise ValueError('Attribute span outside source')
            attribute['source'] = source[start:end].decode('utf-8')
    return result


def literal_docs(attributes):
    return [attribute['doc_text'] for attribute in attributes
            if attribute['path'] == 'doc' and attribute['doc_text'] is not None]


def controls(binary):
    source = '''//! file scope
// ordinary comment, not docs
/// 中文 function
#[doc = "second line"]
fn outer() { fn nested() {} }
mod child {
    //! child scope
    /// method purpose
    pub fn member() {}
}
#[doc = include_str!("missing.md")]
fn included() {}
#[cfg_attr(feature = "extra", doc = "conditional")]
fn conditional() {}
trait Contract { /// declaration
    fn required();
}
hidden! { /// generated
    fn invisible() {}
}
'''
    result = parse(binary, source.encode())
    named = {unit['name']: unit for unit in result['units'] if unit['name']}
    assert literal_docs(result['file_attributes']) == [' file scope']
    assert literal_docs(named['outer']['attributes']) == [' 中文 function', 'second line']
    assert literal_docs(named['nested']['attributes']) == []
    assert literal_docs(named['child']['attributes']) == [' child scope']
    assert literal_docs(named['member']['attributes']) == [' method purpose']
    assert named['child']['attributes'][0]['style'] == 'inner'
    assert literal_docs(named['included']['attributes']) == []
    assert literal_docs(named['conditional']['attributes']) == []
    assert named['required']['body_range'] is None
    assert 'invisible' not in named
    assert named['outer']['attributes'][0]['source'] == '/// 中文 function'
    try:
        parse(binary, b'fn broken( {')
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid syntax accepted')
    return {'input': source, 'parsed': result, 'invalid_input_rejected': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    control = controls(binary)
    prior = json.loads((CORPUS / 'report.json').read_text())
    for name in ['units.json', 'sources.zip']:
        if digest(CORPUS / name) != prior['artifacts_sha256'][name]:
            raise ValueError('Corpus identity mismatch')
    units = json.loads((CORPUS / 'units.json').read_text())
    files = {}
    with zipfile.ZipFile(CORPUS / 'sources.zip') as archive:
        for path in sorted(archive.namelist()):
            source = archive.read(path)
            files[path] = {'source_sha256': hashlib.sha256(source).hexdigest(),
                           **parse(binary, source)}
    bindings = []
    for unit in units:
        file = files[unit['path']]
        if file['source_sha256'] != unit['source_sha256']:
            raise ValueError('File identity mismatch')
        matches = [(index, node) for index, node in enumerate(file['units'])
                   if node['kind'] == unit['kind'] and node['name'] == unit['name']
                   and node['range'] == unit['original_range']
                   and node.get('signature_range', [None])[0] == unit['range'][0]
                   and node.get('body_range') and node['body_range'][1] == unit['range'][1]]
        if len(matches) != 1:
            raise ValueError(f"Non-unique binding for {unit['id']}")
        index, node = matches[0]
        docs = literal_docs(node['attributes'])
        bindings.append({'unit_id': unit['id'], 'path': unit['path'], 'package': unit['package'],
                         'node_index': index, 'literal_doc_nonempty': any(text.strip() for text in docs),
                         'doc_text': '\n'.join(docs), 'ancestor_indices': node['ancestors'],
                         'test_path_hint': unit['test_path_hint']})
    groups = {}
    for package in sorted({unit['package'] for unit in units}):
        selected = [binding for binding in bindings if binding['package'] == package]
        groups[package] = {'functions': len(selected), 'with_literal_docs': sum(
            binding['literal_doc_nonempty'] for binding in selected)}
    attributes = [attribute for file in files.values()
                  for owner in [dict(attributes=file['file_attributes']), *file['units']]
                  for attribute in owner['attributes']]
    output = {'files.json': files, 'bindings.json': bindings, 'controls.json': control}
    for name, value in output.items():
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(__file__, args.output / 'runner.py')
    project = ROOT / 'research/tools/rust-syntax-probe'
    for original, name in [('src/main.rs', 'probe.rs'), ('Cargo.toml', 'Cargo.toml'), ('Cargo.lock', 'Cargo.lock')]:
        shutil.copyfile(project / original, args.output / name)
    report = {
        'schema': 'source-doc-inventory/1', 'revision': prior['revision'],
        'files': len(files), 'bound_functions': len(bindings),
        'with_literal_docs': sum(binding['literal_doc_nonempty'] for binding in bindings),
        'by_package': groups,
        'syntax_objects': dict(Counter(node['kind'] for file in files.values() for node in file['units'])),
        'nonliteral_doc_attributes': sum(attribute['path'] == 'doc' and attribute['doc_text'] is None
                                         for attribute in attributes),
        'cfg_attr_occurrences': sum(attribute['path'] == 'cfg_attr' for attribute in attributes),
        'limitations': ['Four-package archived scope, not whole repository',
                        'No cfg evaluation, macro expansion, include_str resolution or inherited trait docs',
                        'File-scope docs not automatically classified as crate or module docs',
                        'Supported syntax objects only; no fields, constants or aliases indexed as owners',
                        'Ancestor context is not copied into direct documentation',
                        'Documentation presence is not correctness or clone relevance'],
        'binary_sha256': digest(binary), 'corpus_report_sha256': digest(CORPUS / 'report.json'),
        'artifact_sha256': {path.name: digest(path) for path in args.output.iterdir() if path.is_file()},
        'retrieval_experiment': 'not_run',
    }
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['files', 'bound_functions', 'with_literal_docs', 'by_package']}))


if __name__ == '__main__':
    main()
