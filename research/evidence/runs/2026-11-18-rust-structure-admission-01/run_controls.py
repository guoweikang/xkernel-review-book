import hashlib
import json
import pathlib
import platform
import subprocess
import time

RUN = pathlib.Path(__file__).resolve().parent
ROOT = RUN.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (RUN / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    protocol = json.loads((RUN / 'protocol.json').read_text())
    identities = {key: digest(ROOT / protocol[key]) for key in ('binary', 'source')}
    assert all(identities[key] == protocol[key + '_sha256'] for key in identities)
    save('execution-start.json', {'protocol_sha256': digest(RUN / 'protocol.json'),
         'runner_sha256': digest(pathlib.Path(__file__)), 'identities': identities,
         'python': platform.python_version(), 'platform': platform.platform(),
         'started_unix': time.time()})
    results = []
    for control in protocol['controls']:
        prefix = control['id']
        source = control['source'].encode()
        (RUN / (prefix + '.rs')).write_bytes(source)
        started = time.perf_counter()
        result = {'id': prefix, 'source_sha256': hashlib.sha256(source).hexdigest(),
                  'argv': [str(ROOT / protocol['binary'])]}
        try:
            process = subprocess.run(result['argv'], input=source, capture_output=True,
                                     timeout=protocol['execution']['timeout_seconds_each'])
            stdout, stderr = process.stdout, process.stderr
            result['exit_code'] = process.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b'', error.stderr or b''
            result['failure'] = 'timeout'
        result['elapsed_seconds'] = time.perf_counter() - started
        (RUN / (prefix + '.stdout')).write_bytes(stdout)
        (RUN / (prefix + '.stderr')).write_bytes(stderr)
        try:
            parsed = json.loads(stdout)
            result['output'] = parsed
            result['range_slices'] = [source[site['range'][0]:site['range'][1]].decode()
                                      for site in parsed['sites']]
            result['site_keys'] = sorted({key for site in parsed['sites'] for key in site})
        except (ValueError, KeyError, TypeError) as error:
            result['decode_failure'] = str(error)
        save(prefix + '.json', result)
        results.append(result)
    after = {key: digest(ROOT / protocol[key]) for key in identities}
    projection = lambda result: [(site['kind'], site['name'], site['deferred_depth'])
                                for site in result.get('output', {}).get('sites', [])]
    save('summary.json', {'invocations': len(results), 'source_binary_unchanged': after == identities,
         'protocol_unchanged': digest(RUN / 'protocol.json') == json.loads((RUN / 'execution-start.json').read_text())['protocol_sha256'],
         'statuses': [result.get('output', {}).get('status') for result in results],
         'control_01_02_call_projection_equal': projection(results[0]) == projection(results[1]),
         'unexpected_failures': [result['id'] for result in results if 'failure' in result or 'decode_failure' in result or result.get('exit_code') != 0],
         'resolved_edges': 0, 'compiler_runs': 0, 'models': 0})


if __name__ == '__main__':
    main()
