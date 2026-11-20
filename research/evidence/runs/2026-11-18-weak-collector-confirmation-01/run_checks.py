import hashlib
import json
import platform
import subprocess
from pathlib import Path

RUN = Path(__file__).resolve().parent
BOOK = RUN.parents[3]
PRIOR = RUN.parent / '2026-11-18-call-subset-review-01'
REVISION = '7e3ac94431a0dbb376d2fc8d85098deeff1bba09'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*arguments):
    return subprocess.check_output(['git', '-C', '/root/codes/x-kernel', *arguments])


def method(text, name):
    start = text.index('    fn ' + name + '(')
    opening = text.index('{', start)
    depth = 1
    position = opening + 1
    while depth:
        depth += (text[position] == '{') - (text[position] == '}')
        position += 1
    return text[start:position]


def loc(text):
    return sum(bool(line.strip()) and not line.lstrip().startswith('//') for line in text.splitlines())


def save(name, data):
    (RUN / name).write_text(json.dumps(data, indent=2) + '\n')


queue_bytes = (PRIOR / 'queue.json').read_bytes()
queue = json.loads(queue_bytes)
case = json.loads((PRIOR / 'reviewer/cases.json').read_text())[0]
assert queue[0]['slot'] == 1
assert case['case_id'] == 'case-001' and case['source_revision'] == REVISION
assert [member['id'] for member in queue[0]['members']] == [member['id'] for member in case['members']]
assert [member['name'] for member in case['members']] == ['live_super_blocks', 'live_inodes']
identities = []
for member in case['members']:
    source = (PRIOR / 'reviewer' / member['review_files']['source']).read_bytes()
    snippet = (PRIOR / 'reviewer' / member['review_files']['snippet']).read_bytes()
    assert digest(source) == member['source_sha256']
    assert digest(snippet) == member['sha256']
    assert source[slice(*member['range'])] == snippet
    assert source == git('show', REVISION + ':' + member['path'])
    assert source == (RUN / 'sources' / member['path']).read_bytes()
    assert source[:member['range'][0]].count(b'\n') + 1 == member['start_line']
    assert source[:member['range'][1]].count(b'\n') + 1 == member['end_line']
    identities.append({'name': member['name'], 'path': member['path'],
                       'source_sha256': digest(source), 'snippet_sha256': digest(snippet),
                       'lines': [member['start_line'], member['end_line']]})
for path in sorted((RUN / 'sources').rglob('*')):
    if path.is_file():
        relative = path.relative_to(RUN / 'sources').as_posix()
        assert path.read_bytes() == git('show', REVISION + ':' + relative)
        identities.append({'path': relative, 'sha256': digest(path.read_bytes()),
                           'blob': git('rev-parse', REVISION + ':' + relative).decode().strip()})
source_text = source.decode()
original = (RUN / 'original.txt').read_text()
assert original == method(source_text, 'live_super_blocks') + '\n\n' + method(source_text, 'live_inodes') + '\n'
fixture = (RUN / 'fixture.rs').read_text()
proposal = (RUN / 'proposed.txt').read_text()
assert method(fixture, 'live_super_blocks') == method(source_text, 'live_super_blocks')
assert method(fixture, 'live_inodes') == method(source_text, 'live_inodes').replace('.lock()', '.lock().unwrap()')
for name in ('live_super_blocks', 'live_inodes'):
    expected = method(proposal, name).replace('fn ' + name, 'fn candidate_' + name)
    expected = expected.replace('.lock()', '.lock().unwrap()')
    assert method(fixture, 'candidate_' + name) == expected
helper = proposal.split('\n\n')[0]
assert helper in fixture
assert helper.count('.upgrade()') == 1
assert helper.count('.retain(') == 1
assert '.clone()' not in helper
for name in ('live_super_blocks', 'live_inodes'):
    assert method(source_text, name).count('.upgrade()') == 1
version = subprocess.check_output(['rustc', '+stable', '-vV'], text=True)
assert '\nrelease: 1.97.1\n' in version
rustc = subprocess.check_output(['rustup', 'which', '--toolchain', 'stable', 'rustc'], text=True).strip()
commands = []
for mode, optimization, assertions in [('debug', '0', 'yes'), ('opt', '3', 'no')]:
    commands.append([rustc, '--edition=2024', '--test', 'fixture.rs', '-C', 'opt-level=' + optimization,
                     '-C', 'debug-assertions=' + assertions, '-o', 'fixture-' + mode])
    for repeat in (1, 2):
        commands.append(['./fixture-' + mode, '--test-threads=1', '--nocapture'])
freeze = {
    'revision': REVISION, 'queue_slot': 1, 'queue_sha256': digest(queue_bytes),
    'selection': 'first frozen slot, no outcome or score reselection',
    'identities': identities, 'static_body_adapters_verified': True,
    'original_loc': [loc(method(source_text, name)) for name in ('live_super_blocks', 'live_inodes')],
    'candidate_loc': [loc(helper), loc(method(proposal, 'live_super_blocks')), loc(method(proposal, 'live_inodes'))],
    'unchanged_registry_wrapper_loc': 3,
    'rustc_version_verbose': version, 'rustc_executable': rustc, 'host': platform.platform(),
    'commands': commands, 'command_cwd': str(RUN), 'timeout_seconds_each': 60,
    'input_hashes': {name: digest((RUN / name).read_bytes()) for name in
                     ['protocol.txt', 'fixture.rs', 'original.txt', 'proposed.txt', 'run_checks.py']},
    'runtime_not_yet_started': True,
}
save('execution-freeze.json', freeze)
print('PREEXECUTION PASS: pinned identities, first queue slot, exact body adapters, helper, costs and runtime frozen', flush=True)
results = []
for index, command in enumerate(commands, 1):
    if command[0].startswith('./') and not (RUN / command[0][2:]).exists():
        results.append({'index': index, 'command': command, 'status': 'skipped_missing_binary'})
        save('results.json', results)
        continue
    try:
        completed = subprocess.run(command, cwd=RUN, capture_output=True, text=True, timeout=60)
        stdout, stderr, status = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b''
        stderr = error.stderr or b''
        stdout = stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
        status = 'timeout'
    (RUN / f'command-{index:02d}.stdout.log').write_text(stdout)
    (RUN / f'command-{index:02d}.stderr.log').write_text(stderr)
    results.append({'index': index, 'command': command, 'exit_status': status,
                    'stdout': f'command-{index:02d}.stdout.log', 'stderr': f'command-{index:02d}.stderr.log'})
    save('results.json', results)
    print(f'command-{index:02d} status={status}', flush=True)
for name, expected in freeze['input_hashes'].items():
    assert digest((RUN / name).read_bytes()) == expected
print('POSTEXECUTION PASS: frozen inputs unchanged', flush=True)
if any(result.get('exit_status') != 0 for result in results):
    raise SystemExit(1)
