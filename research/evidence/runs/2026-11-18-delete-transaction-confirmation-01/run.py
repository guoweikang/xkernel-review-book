import hashlib
import json
import os
import pathlib
import subprocess
import time

RUN = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def command(directory, name, argv, env, timeout):
    start = time.perf_counter()
    result = {'argv': list(map(str, argv))}
    try:
        process = subprocess.run(result['argv'], env=env, capture_output=True, timeout=timeout)
        stdout, stderr = process.stdout, process.stderr
        result['exit_code'] = process.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b'', error.stderr or b''
        result['timeout'] = True
    result['elapsed_seconds'] = time.perf_counter() - start
    (directory / (name + '.stdout')).write_bytes(stdout)
    (directory / (name + '.stderr')).write_bytes(stderr)
    save(directory / (name + '.json'), result)
    return result, stdout


def main():
    protocol = json.loads((RUN / 'protocol.json').read_text())
    frozen = {name: sha(RUN / name) for name in ['protocol.json', 'witness.rs', 'run.py']}
    save(RUN / 'freeze.json', frozen)
    env = dict(os.environ, RUSTUP_TOOLCHAIN='1.95.0-x86_64-unknown-linux-gnu')
    command(RUN, 'rustc-version', ['rustc', '--version', '--verbose'], env, 10)
    outputs = {}
    for label, level in [('debug', '0'), ('opt', '3')]:
        directory = RUN / label
        directory.mkdir()
        binary = directory / 'witness'
        build, _ = command(directory, 'compile', ['rustc', '--edition=2024', '-C', 'opt-level=' + level,
            str(RUN / 'witness.rs'), '-o', str(binary)], env, 30)
        if build.get('exit_code') != 0:
            outputs[label] = {'passed': False, 'stage': 'compile'}
            continue
        execution, stdout = command(directory, 'execute', [binary], env, 5)
        observations = []
        try:
            for line in stdout.decode().splitlines():
                condition, variant, outcome, events = line.split('\t')
                expected = protocol['expected'][condition]
                observations.append({'condition': condition, 'variant': variant, 'outcome': outcome,
                    'events': events.split(','), 'matches_frozen': outcome == expected['error'] and
                    events.split(',') == expected.get(variant, expected.get('both'))})
            passed = execution.get('exit_code') == 0 and len(observations) == 6 and all(row['matches_frozen'] for row in observations)
            outputs[label] = {'passed': passed, 'observations': observations, 'binary_sha256': sha(binary)}
        except Exception as error:
            outputs[label] = {'passed': False, 'decode_error': repr(error)}
        save(directory / 'observations.json', outputs[label])
    save(RUN / 'results.json', {'builds': outputs, 'source_protocol_runner_unchanged':
        all(sha(RUN / name) == expected for name, expected in frozen.items()),
        'kernel_executions': 0, 'integration_repairs': 0, 'comparison': 'Exact events and error, not timing'})


if __name__ == '__main__':
    main()
