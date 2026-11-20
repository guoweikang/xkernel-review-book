import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNS = HERE.parent
TREATMENT = RUNS / '2026-11-18-rust-structure-if-01'
BASELINE = RUNS / '2026-11-18-rust-structure-prototype-01'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    assert not (HERE / 'results.json').exists(), 'Refusing overwrite'
    checker_path = ROOT / 'scripts/check_rust_structure_output.py'
    census_path = RUNS / '2026-11-18-rust-subtree-admission-01/census.py'
    checker = load('checker', checker_path)
    census = load('census', census_path)
    baseline_paths = sorted((BASELINE / 'corpus').glob('*.rs'))
    treatment_paths = sorted((TREATMENT / 'corpus').glob('*.rs'))
    assert len(baseline_paths) == len(treatment_paths) == 8
    assert [path.name for path in baseline_paths] == [path.name for path in treatment_paths]
    for old, new in zip(baseline_paths, treatment_paths):
        assert old.read_bytes() == new.read_bytes(), new
    attempts = sorted(TREATMENT.glob('attempt-*'))
    assert attempts
    controls = sorted(attempts[-1].glob('control-*.rs'))
    assert 12 <= len(controls) <= 16
    results = []
    for source in controls + treatment_paths:
        payload = json.loads(source.with_suffix('.stdout').read_text())
        results.append({'source': str(source.relative_to(ROOT)),
                        'output_sha256': hashlib.sha256(source.with_suffix('.stdout').read_bytes()).hexdigest(),
                        'result': checker.check(source.read_bytes(), payload)})
    census.INPUT = TREATMENT / 'corpus'
    first = census.measure()
    assert first == census.measure()
    baseline = json.loads((census.HERE / 'results.json').read_text())
    report = {'checks': results, 'census': first, 'repeat_equal': True,
              'source_identity_8_of_8': True,
              'measurement_caveat': 'Census embedded protocol hash identifies unchanged baseline measurement rule; treatment protocol hash below identifies this comparison.',
              'treatment_protocol_sha256': hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest(),
              'checker_sha256': hashlib.sha256(checker_path.read_bytes()).hexdigest(),
              'baseline_summary': {key: value for key, value in baseline.items() if key != 'units'}}
    (HERE / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in first.items() if key != 'units'}))


if __name__ == '__main__':
    main()
