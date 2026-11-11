"""Recheck archived paired logs, input identities and path-normalized configuration."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from check_metadata_test_log import evaluate, expected_tests


def check(directory):
    report = json.loads((directory / 'report.json').read_text())
    if report['status'] != 'paired_tests_passed':
        raise ValueError('Paired runner did not pass')
    for name, expected in report['artifact_sha256'].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Artifact identity differs: ' + name)
    with gzip.open(directory / 'preboot.img.gz', 'rb') as stream:
        image = stream.read()
    if len(image) != 64 * 1024 * 1024 or hashlib.sha256(image).hexdigest() != report['template_sha256']:
        raise ValueError('Preboot template differs')
    configs = []
    commands = []
    for variant in ['original', 'candidate']:
        run = report['runs'][variant]
        if run['initial_disk_sha256'] != report['template_sha256']:
            raise ValueError('Initial disk differs')
        step = next(step for step in report['steps'] if step['name'] == variant)
        gate = evaluate((directory / (variant + '.log')).read_text(), step['exit_code'], expected_tests())
        if not gate['passed'] or gate != run['test_gate']:
            raise ValueError('Test result differs')
        target = next(arg.split('=', 1)[1] for arg in step['command'] if arg.startswith('TARGET_DIR='))
        configs.append((directory / (variant + '-.cargo__.xconfig.toml')).read_text().replace(target, '<TARGET>'))
        commands.append([arg.split('=', 1)[0] + '=<ISOLATED_PATH>'
                         if arg.startswith(('TARGET_DIR=', 'DISK_IMG=')) else arg for arg in step['command']])
    if configs[0] != configs[1] or commands[0] != commands[1]:
        raise ValueError('Configuration or invocation differs beyond isolated paths')
    for suffix in ['.config', 'Cargo.lock', 'xtask__Cargo.lock']:
        if (directory / ('original-' + suffix)).read_bytes() != (directory / ('candidate-' + suffix)).read_bytes():
            raise ValueError('Input differs: ' + suffix)
    return {'passed': True, 'tests_each': 94, 'preboot_template_verified': True,
            'config_and_locks_equal': True, 'generated_config_equal_except_target_path': True,
            'commands_equal_except_disk_and_target_paths': True,
            'production_build': 'not_run', 'net_benefit': 'unverified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    if args.self_check:
        check(args.directory)
        for mutation in ['config', 'disk', 'exit', 'command']:
            with tempfile.TemporaryDirectory() as temporary:
                copied = Path(temporary) / 'run'
                shutil.copytree(args.directory, copied)
                report = json.loads((copied / 'report.json').read_text())
                if mutation == 'config':
                    name = 'candidate-.cargo__.xconfig.toml'
                    with (copied / name).open('a') as stream:
                        stream.write('\n# negative-control mismatch\n')
                    report['artifact_sha256'][name] = hashlib.sha256((copied / name).read_bytes()).hexdigest()
                elif mutation == 'disk':
                    report['runs']['candidate']['initial_disk_sha256'] = '0' * 64
                else:
                    step = next(step for step in report['steps'] if step['name'] == 'candidate')
                    if mutation == 'exit':
                        step['exit_code'] = 124
                    else:
                        step['command'].append('SMP=1')
                (copied / 'report.json').write_text(json.dumps(report))
                try:
                    check(copied)
                except ValueError:
                    continue
                raise AssertionError('Accepted negative control: ' + mutation)
        print('PASS: real paired evidence accepted; 4 input/result mismatch controls rejected; no kernel rerun')
        return
    print(json.dumps(check(args.directory), indent=2))


if __name__ == '__main__':
    main()
