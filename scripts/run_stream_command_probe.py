"""Execute exact archived adapter bodies with a bounded event-trace model."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(rows):
    expected = {
        'complete': [('Ok(4)', 0, 104, [4]), ('Ok(4)', 0, 104, [4])],
        'empty': [('Ok(0)', 0, 100, []), ('Ok(0)', 0, 100, [])],
        'oversize': [('Ok(4097)', 0, 4197, [4096, 1]), ('Err(FileTooLarge)', 4097, 100, [])],
        'short_success': [('Ok(4)', 0, 104, [2, 2]), ('Ok(4)', 0, 104, [4])],
        'short_then_fault': [('Ok(2)', 2, 102, [2]), ('Err(BadAddress)', 4, 100, [])],
        'callback_fault': [('Err(BadAddress)', 4, 100, [4]), ('Err(BadAddress)', 4, 100, [4])],
    }
    assert len(rows) == 12
    indexed = {(row['scenario'], row['adapter']): row for row in rows}
    assert len(indexed) == 12
    for scenario, outcomes in expected.items():
        for adapter, outcome in zip(('scalar', 'command'), outcomes):
            row = indexed[(scenario, adapter)]
            actual = (row['result'], row['remaining'], row['position'], [len(call['payload']) for call in row['calls']])
            assert actual == outcome, (scenario, adapter, actual, outcome)
            cursor = 0
            for call in row['calls']:
                assert call['offset'] == 100 + cursor
                assert call['payload'] == [index % 251 for index in range(cursor, cursor + len(call['payload']))]
                cursor += len(call['payload'])
    assert indexed[('short_then_fault', 'scalar')]['trace'] == ['copy:2', 'callback:2:100', 'rewind:0', 'copy:BadAddress:no_cursor_effect']
    assert indexed[('short_then_fault', 'command')]['trace'] == ['copy:2', 'copy:BadAddress:no_cursor_effect', 'rewind:2']
    assert indexed[('oversize', 'command')]['trace'] == []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and all(character.isalnum() or character in '-_' for character in args.run_id)
    output = ROOT / 'research/evidence/runs' / args.run_id
    output.mkdir()
    protocol_path = ROOT / 'research/protocols/stream-command-traces-v1.json'
    template_path = ROOT / 'research/tools/stream-command-probe.rs.in'
    protocol = json.loads(protocol_path.read_text())
    seed = ROOT / protocol['seed']
    card = json.loads((seed / 'card.json').read_text())
    for member in card['members']:
        assert sha(seed / member['unit_file']) == member['sha256']
    source = template_path.read_text().replace('@@SCALAR@@', (seed / '1-unit.rs').read_text()).replace('@@COMMAND@@', (seed / '2-unit.rs').read_text())
    compiler = ['rustup', 'run', protocol['toolchain'], 'rustc']
    inputs = [protocol_path, template_path, Path(__file__), seed / 'card.json', seed / '1-unit.rs', seed / '2-unit.rs']
    manifest = {'scope': protocol['model'], 'revision': card['revision'],
                'compiler': subprocess.check_output(compiler + ['-vV'], text=True),
                'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in inputs}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'probe.rs').write_text(source)
    shutil.copy2(protocol_path, output / 'protocol.json')
    shutil.copy2(__file__, output / 'runner.py')
    commands = []
    reference = None
    with tempfile.TemporaryDirectory(prefix='stream-command-') as temporary:
        for repeat in range(1, 3):
            for mode in protocol['build_modes']:
                identity = f'{mode}-{repeat}'
                executable = str(Path(temporary) / identity)
                command = compiler + ['--edition=2024', str(output / 'probe.rs'), '-o', executable]
                if mode == 'release':
                    command += ['-O']
                for phase, argv in [('compile', command), ('execute', [executable])]:
                    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
                    (output / f'{identity}-{phase}.stdout').write_text(result.stdout)
                    (output / f'{identity}-{phase}.stderr').write_text(result.stderr)
                    commands.append({'id': identity, 'phase': phase, 'argv': argv, 'exit': result.returncode})
                    (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
                    assert result.returncode == 0, (identity, phase)
                rows = [json.loads(line) for line in result.stdout.splitlines()]
                check(rows)
                if reference is not None:
                    assert result.stdout == reference
                reference = result.stdout
    report = {'passed': True, 'binaries': 4, 'scenario_adapter_runs': 48,
              'unique_scenarios': 6, 'repeat_and_mode_trace_identity': True,
              'scope': 'Exact archived function bodies with modeled dependencies; not real iterator or kernel execution',
              'conclusion': 'Direct substitution differs on short-success, short-then-fault and oversize; local sharing remains undecided',
              'artifact_sha256': {path.name: sha(path) for path in output.iterdir() if path.is_file()}}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
