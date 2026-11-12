"""Freeze, execute and audit the complete bounded 2x2 InMap batch."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from check_inmap_loop_probe import audit


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def prepare(batch):
    if batch.exists():
        raise SystemExit('Batch already exists; will not overwrite')
    extraction = ROOT / 'research/evidence/runs/2026-11-12-inmap-declarations-03'
    population_run = ROOT / 'research/evidence/runs/2026-11-11-inmap-loop-01'
    for run in (extraction, population_run):
        report = json.loads((run / 'report.json').read_text())
        assert report['returncode'] == 0
        for name, checksum in report['artifact_sha256'].items():
            assert digest(run / name) == checksum
    population = set((population_run / 'filtered-classes.txt').read_text().splitlines())
    types = {line.split('\t')[0] for line in (extraction / 'declared-method-types.tsv').read_text().splitlines()}
    assert population <= types
    methods = defaultdict(set)
    for row in (extraction / 'declared-methods.tsv').read_text().splitlines():
        owner, method, source = row.split('\t')
        if owner in population and '$' not in owner:
            methods[owner].add(method)
    batch.mkdir(parents=True)
    vocabulary = batch / 'declared-method-input.tsv'
    vocabulary.write_text(''.join(owner + '\t' + ','.join(sorted(methods[owner])) + '\n' for owner in sorted(population)))
    frozen = [ROOT / 'scripts/run_inmap_input_probe.py', ROOT / 'scripts/run_inmap_factorial.py',
              ROOT / 'scripts/check_inmap_loop_probe.py', ROOT / 'scripts/scc_namespace.sh',
              ROOT / 'research/tools/InMapLoopProbe.java', ROOT / 'research/tools/InMapTrace.java',
              ROOT / 'research/tools/InMapUniqueMaximum.txt',
              ROOT / 'research/evidence/runs/2026-11-11-inmap-config-audit-02/config-single.txt',
              ROOT / 'research/evidence/runs/2026-11-11-inmap-fetch-01/downloads.json',
              extraction / 'report.json', population_run / 'report.json', vocabulary]
    runs = []
    for repeat in (1, 2):
        for condition in ('O0', 'OD', 'U0', 'UD'):
            run_id = batch.name + '-' + condition.lower() + '-' + str(repeat)
            command = [sys.executable, str(ROOT / 'scripts/run_inmap_input_probe.py'), '--run-id', run_id,
                       '--missing-method-loop', '--trace-queries']
            if condition.startswith('U'):
                command.append('--unique-maximum-control')
            if condition.endswith('D'):
                command.extend(['--declared-method-input', str(vocabulary)])
            runs.append({'id': run_id, 'condition': condition, 'repeat': repeat, 'command': command})
    manifest = {'question': 'effect of top-level declared-method feedback separately from selector changes',
                'scope': 'development experiment on fixed JabRef snapshot; not original paper reproduction',
                'budget': {'runs': 8, 'wall_seconds_per_runner': 240, 'isolated_process_seconds': 180,
                           'cpu_seconds': 120, 'java_heap_mb': 512, 'maximum_loop_pages': 200},
                'primary_metrics': ['accepted / population', 'accepted recommendation events / all recommendation events'],
                'telemetry': ['accepted snapshots at each page', 'raw and parsed queries', 'method counts and keyword budget'],
                'protocol_amendment_before_outcomes': 'Uses parsed named-type inventory; only exact top-level owners enter D. No source offsets or per-exclusion-category counters yet; no claims on extraction recall. Query records preserve final text and method counts, not token-by-token provenance. Same observation insertions and limits for all conditions.',
                'population': len(population), 'nonempty': sum(bool(methods[owner]) for owner in population),
                'method_pairs': sum(len(methods[owner]) for owner in population), 'runs': runs,
                'frozen_sha256': {str(path.relative_to(ROOT)): digest(path) for path in frozen}}
    save(batch / 'manifest.json', manifest)
    (batch / 'manifest.sha256').write_text(digest(batch / 'manifest.json') + '\n')
    save(batch / 'state.json', {run['id']: {'status': 'pending'} for run in runs})


def execute(batch):
    assert digest(batch / 'manifest.json') == (batch / 'manifest.sha256').read_text().strip()
    manifest = json.loads((batch / 'manifest.json').read_text())
    for path, checksum in manifest['frozen_sha256'].items():
        assert digest(ROOT / path) == checksum, path
    state = json.loads((batch / 'state.json').read_text())
    for run in manifest['runs']:
        if state[run['id']]['status'] != 'pending':
            continue
        state[run['id']] = {'status': 'running'}
        save(batch / 'state.json', state)
        try:
            result = subprocess.run(run['command'], cwd=ROOT, capture_output=True, timeout=240)
            (batch / (run['id'] + '.stdout')).write_bytes(result.stdout)
            (batch / (run['id'] + '.stderr')).write_bytes(result.stderr)
            state[run['id']] = {'status': 'complete' if result.returncode == 0 else 'failed', 'returncode': result.returncode}
        except subprocess.TimeoutExpired as error:
            (batch / (run['id'] + '.stdout')).write_bytes(error.stdout or b'')
            (batch / (run['id'] + '.stderr')).write_bytes(error.stderr or b'')
            state[run['id']] = {'status': 'timeout'}
        save(batch / 'state.json', state)
        print(run['id'], state[run['id']]['status'], flush=True)


def analyze(batch):
    manifest = json.loads((batch / 'manifest.json').read_text())
    state = json.loads((batch / 'state.json').read_text())
    summaries = {}
    for run in manifest['runs']:
        if state[run['id']]['status'] != 'complete':
            raise SystemExit('Incomplete batch; failures retained; no favorable-only comparison')
        root = ROOT / 'research/evidence/runs' / run['id']
        summaries[run['id']] = audit(root)
    for condition in ('O0', 'OD', 'U0', 'UD'):
        runs = [run for run in manifest['runs'] if run['condition'] == condition]
        assert summaries[runs[0]['id']] == summaries[runs[1]['id']]
        for name in ('pages.tsv', 'acceptedMappings.tsv', 'rejectedMappings.tsv', 'trace-queries.tsv', 'trace-accepted.tsv'):
            assert (ROOT / 'research/evidence/runs' / runs[0]['id'] / name).read_bytes() == (ROOT / 'research/evidence/runs' / runs[1]['id'] / name).read_bytes(), (condition, name)
    baseline = ROOT / 'research/evidence/runs' / manifest['runs'][0]['id']
    first_queries = None
    for run in manifest['runs']:
        root = ROOT / 'research/evidence/runs' / run['id']
        for name in ('config-single.txt', 'dependencies.json', 'filtered-classes.txt', 'oracle.tsv'):
            assert (root / name).read_bytes() == (baseline / name).read_bytes(), name
        query_rows = (root / 'trace-queries.tsv').read_text().splitlines()
        initial = [row for row in query_rows if row.startswith('1\t')]
        if first_queries is None:
            first_queries = initial
        assert len(initial) == 6 and initial == first_queries
        if run['condition'].endswith('D'):
            assert digest(root / 'declared-method-input.tsv') == digest(batch / 'declared-method-input.tsv')
    conditions = {run['condition']: summaries[run['id']] for run in manifest['runs'] if run['repeat'] == 1}
    effects = {}
    for metric in ('accepted', 'rejected', 'recommendations', 'population_mapping_fraction', 'oracle_agreement_precision'):
        values = {condition: summary[metric] for condition, summary in conditions.items()}
        effects[metric] = {'OD-O0': values['OD'] - values['O0'], 'UD-U0': values['UD'] - values['U0'],
                           'U0-O0': values['U0'] - values['O0'], 'UD-OD': values['UD'] - values['OD'],
                           'interaction': (values['UD'] - values['U0']) - (values['OD'] - values['O0'])}
    save(batch / 'analysis.json', {'conditions': conditions, 'effects': effects, 'repeat_core_and_queries_identical': True,
                                   'first_empty_feedback_queries_identical': True, 'scope': manifest['scope']})
    print(json.dumps({key: {metric: value[metric] for metric in ('accepted', 'rejected', 'recommendations', 'pages')} for key, value in conditions.items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'execute', 'analyze'))
    parser.add_argument('--batch-id', required=True)
    args = parser.parse_args()
    if not args.batch_id or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in args.batch_id):
        parser.error('simple lowercase batch-id required')
    batch = ROOT / 'research/evidence/runs' / args.batch_id
    {'prepare': prepare, 'execute': execute, 'analyze': analyze}[args.phase](batch)


if __name__ == '__main__':
    main()
