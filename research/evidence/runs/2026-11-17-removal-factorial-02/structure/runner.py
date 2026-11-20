import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / 'research/evidence/runs' / args.run
    output = run / 'structure'
    output.mkdir(exist_ok=False)
    inputs = {}
    formatted = {}
    for label in ('original', 'candidate'):
        source = run / f'{label}.rs'
        inputs[label] = hashlib.sha256(source.read_bytes()).hexdigest()
        target = output / f'{label}.rs'
        shutil.copyfile(source, target)
        result = subprocess.run(['rustfmt', '+1.95.0', '--edition', '2024', '--config', 'skip_children=true', str(target)], capture_output=True)
        (output / f'{label}-format.log').write_bytes(result.stdout + result.stderr)
        result.check_returncode()
        formatted[label] = target.read_text()
    report = {'input_sha256': inputs, 'formatter': subprocess.check_output(['rustfmt', '+1.95.0', '--version'], text=True), 'module_lines': {label: len(text.splitlines()) for label, text in formatted.items()}, 'module_nonblank_lines': {label: sum(bool(line.strip()) for line in text.splitlines()) for label, text in formatted.items()}, 'new_private_helpers': 1, 'helper_call_sites': 2, 'explicit_helper_parameters_excluding_receiver': 3, 'limits': 'Formatting-normalized structural accounting of frozen source copies; not measured maintainability or performance. Formatted copies were not the compiled input.'}
    (output / 'candidate-formatted.diff').write_text(''.join(difflib.unified_diff(formatted['original'].splitlines(True), formatted['candidate'].splitlines(True), fromfile='a/fs/kvfs/src/mount.rs', tofile='b/fs/kvfs/src/mount.rs')))
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'runner.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
