"""Rust token-tree frontend and reversible SCC bag serialization, not detection."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


def tokenize(binary, content):
    process = subprocess.run([str(binary)], input=content, capture_output=True, check=True, timeout=30)
    result = json.loads(process.stdout)
    if result.get('schema') != 'rust-token-probe/1' or result.get('status') not in {'tokenized', 'rejected'}:
        raise ValueError('Unsupported token frontend response')
    if not isinstance(result.get('tokens'), list) or not all(isinstance(token, str) for token in result['tokens']):
        raise ValueError('Invalid token sequence')
    if result['status'] == 'rejected' and (result['tokens'] or not result.get('error')):
        raise ValueError('Rejected input must not provide usable tokens')
    return result


def encode_bag(tokens, number):
    counts = Counter('t' + token.encode().hex() for token in tokens)
    body = ','.join(f'{token}@@::@@{count}' for token, count in sorted(counts.items()))
    checksum = hashlib.md5(body.encode()).hexdigest()
    return f'1,{number},{len(tokens)},{len(counts)},{checksum}@#@{body}'


def decode_bag(line):
    header, body = line.split('@#@', 1)
    project, number, total, unique, checksum = header.split(',')
    if project != '1' or int(number) < 1 or hashlib.md5(body.encode()).hexdigest() != checksum:
        raise ValueError('Invalid SCC header/checksum')
    decoded = Counter()
    for entry in body.split(',') if body else []:
        token, count = entry.split('@@::@@')
        if not token.startswith('t') or int(count) <= 0:
            raise ValueError('Invalid encoded token or count')
        original = bytes.fromhex(token[1:]).decode()
        if original in decoded:
            raise ValueError('Duplicate token entry')
        decoded[original] = int(count)
    if sum(decoded.values()) != int(total) or len(decoded) != int(unique):
        raise ValueError('Invalid SCC token counts')
    return decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'detector': 'not_run', 'records': [], 'failures': [],
              'minimum_tokens': 65, 'maximum_tokens': 500000}
    shutil.copy2(__file__, args.output / 'frontend.py')
    try:
        binary = args.binary.resolve()
        report['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
        root = Path(__file__).resolve().parents[1]
        checker = root / 'scripts/check_rust_token_bags.py'
        for path in [checker, root / 'research/tools/rust-syntax-probe/src/bin/rust-token-probe.rs',
                     root / 'research/tools/rust-syntax-probe/Cargo.toml',
                     root / 'research/tools/rust-syntax-probe/Cargo.lock']:
            shutil.copy2(path, args.output / path.name)
        validation = subprocess.run(['python3', str(checker), '--binary', str(binary)],
                                    capture_output=True, timeout=90)
        (args.output / 'validation.log').write_bytes(validation.stdout + validation.stderr)
        if validation.returncode:
            raise ValueError('Lexical/serialization regression gate failed')
        report['lexical_regression'] = 'passed'
        source_report = json.loads((args.corpus / 'report.json').read_text())
        if not source_report['passed']:
            raise ValueError('Corpus export did not pass')
        for name, digest in source_report['artifacts_sha256'].items():
            if hashlib.sha256((args.corpus / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Corpus changed: ' + name)
        report['corpus_report_sha256'] = hashlib.sha256((args.corpus / 'report.json').read_bytes()).hexdigest()
        units = json.loads((args.corpus / 'units.json').read_text())
        lines = []
        with zipfile.ZipFile(args.corpus / 'units.zip') as archive:
            for number, unit in enumerate(units, 1):
                content = archive.read(unit['entry'])
                if hashlib.sha256(content).hexdigest() != unit['sha256']:
                    raise ValueError('Unit hash mismatch')
                result = tokenize(binary, content)
                record = {'file_id': number, 'unit_id': unit['id'], 'path': unit['path'],
                          'range': unit['range'], 'start_line': unit['start_line'],
                          'end_line': unit['end_line'], 'status': result['status']}
                if result['status'] == 'rejected':
                    record['error'] = result['error']
                    report['failures'].append(record)
                else:
                    tokens = result['tokens']
                    line = encode_bag(tokens, number)
                    if decode_bag(line) != Counter(tokens):
                        raise ValueError('Token serialization round-trip failed')
                    record.update({'tokens': len(tokens), 'unique_tokens': len(set(tokens)),
                                   'size_eligible': 65 <= len(tokens) <= 500000})
                    lines.append(line)
                report['records'].append(record)
        (args.output / 'blocks.file').write_text('\n'.join(lines) + '\n')
        report['total_units'] = len(units)
        report['tokenized_units'] = len(lines)
        report['size_eligible_units'] = sum(record.get('size_eligible', False) for record in report['records'])
        report['passed'] = not report['failures'] and len(lines) == source_report['units']
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in sorted(args.output.iterdir()) if path.is_file()}
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in {'records', 'failures'}}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
