"""Require the exact fixed source test set; a success banner alone is insufficient."""

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'research/evidence/runs/2026-11-05-source-units-v2-verified/inventory.json'
MODULES = {'fs/kvfs/ut-tests/mount.rs': 'kvfs::mount::tests',
           'fs/kvfs/ut-tests/node_dentry.rs': 'kvfs::node::dentry::tests_dentry'}


def expected_tests():
    raw = INVENTORY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '43a6df7c84117979c0af773357cd754b879b32cdf2cec66c093fdf101e67a7e0':
        raise ValueError('Inventory changed')
    inventory = json.loads(raw)
    expected = []
    for path, module in MODULES.items():
        for unit in inventory['files'][path]['units']:
            attributes = unit['attributes']
            if any(attribute['path'] == 'def_test' for attribute in attributes):
                if unit['ancestors'] or any(attribute['path'] in {'cfg', 'cfg_attr'} for attribute in attributes):
                    raise ValueError('Conditional or nested test requires explicit scope review')
                expected.append(module + '::' + unit['name'])
    if len(expected) != 94 or len(set(expected)) != 94:
        raise ValueError('Fixed test inventory changed')
    return sorted(expected)


def evaluate(log, exit_code, expected):
    results = re.findall(r'\bRESULT\s+(\S+)\s+\.\.\.\s+(ok|FAILED|ignored)\b', log)
    names = [name for name, _ in results]
    return {'passed': exit_code == 0 and log.count('=== UNITTEST_STATUS: ALL_TESTS_PASSED ===') == 1
            and '=== UNITTEST_STATUS: TESTS_FAILED ===' not in log
            and len(names) == len(set(names)) and set(names) == set(expected)
            and all(status == 'ok' for _, status in results),
            'exit_code': exit_code, 'expected': len(expected), 'observed': len(results),
            'missing': sorted(set(expected) - set(names)), 'unexpected': sorted(set(names) - set(expected)),
            'duplicate_results': len(names) - len(set(names)),
            'non_ok': [name for name, status in results if status != 'ok']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--exit-code', type=int)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    expected = expected_tests()
    if args.self_check:
        rows = [f'RESULT {name} ... ok' for name in expected]
        banner = '=== UNITTEST_STATUS: ALL_TESTS_PASSED ==='
        positive = '\n'.join(rows + [banner])
        assert evaluate(positive, 0, expected)['passed']
        negatives = [('\n'.join(rows[1:] + [banner]), 0),
                     (positive + '\n' + rows[0], 0),
                     (positive.replace(' ... ok', ' ... ignored', 1), 0),
                     (positive.replace(' ... ok', ' ... FAILED', 1), 0),
                     (positive + '\nRESULT kvfs::other::test ... ok', 0),
                     (banner, 0), (positive, 124),
                     (positive + '\n=== UNITTEST_STATUS: TESTS_FAILED ===', 0),
                     (positive.replace(banner, ''), 0), (positive + '\n' + banner, 0)]
        assert all(not evaluate(log, code, expected)['passed'] for log, code in negatives)
        print('PASS: synthetic 94-result log accepted; 10 negative controls rejected; no kernel execution')
        return 0
    if args.log is None or args.exit_code is None:
        parser.error('Provide --log and --exit-code, or --self-check')
    result = evaluate(args.log.read_text(), args.exit_code, expected)
    result['log_sha256'] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
