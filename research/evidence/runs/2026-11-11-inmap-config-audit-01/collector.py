"""Audit the archived configuration, without claiming to execute its Java parser."""

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import difflib
import hashlib
import json
from math import prod
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/evidence/runs/2026-11-11-inmap-version-comparison-01/pre-paper-candidate__test-systems__Jabref__config-jabref.json'


def parse(text):
    scalars, arrays = {}, {}
    active = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('//') or line in ('****', '----'):
            continue
        if active is not None:
            if line == '}':
                active = None
            else:
                match = re.fullmatch(r'"(.*)"', line)
                if not match:
                    raise ValueError(f'unsupported array line: {line}')
                arrays[active].append(match[1])
            continue
        match = re.fullmatch(r'(\w+)\s*:\s*\{', line)
        if match:
            active = match[1]
            if active in arrays or active in scalars:
                raise ValueError(f'duplicate setting: {active}')
            arrays[active] = []
            continue
        match = re.fullmatch(r'(\w+)\s*:\s*"(.*)"', line)
        if not match:
            raise ValueError(f'unsupported setting line: {line}')
        if match[1] in arrays or match[1] in scalars:
            raise ValueError(f'duplicate setting: {match[1]}')
        scalars[match[1]] = match[2]
    if active is not None:
        raise ValueError('unclosed array')
    return scalars, arrays


def audit(text):
    scalars, arrays = parse(text)
    owners = defaultdict(list)
    mapping = defaultdict(list)
    module = None
    for entry in arrays['ProgramMapping']:
        if entry.startswith('MODULE : '):
            module = entry.split(':', 1)[1].strip()
        else:
            if module is None:
                raise ValueError('class before module')
            mapping[module].append(entry)
            owners[entry].append(module)
    ranges = {}
    for suffix, step in (
        ('ResultsPerPage', 'ResultsPerPageStep'), ('MNBoostFactor', 'MNBoostFactorStep'),
        ('MDBoostFactor', 'MDBoostFactorStep'), ('Threshold', 'ThresholdStep'),
        ('PenaltyFactor', 'PenaltyFactorStep'), ('InitialMappingFraction', 'InitialMappingFractionStep'),
        ('TechniqueWeighting', 'TechniqueWeightingStep'),
    ):
        minimum, maximum, delta = (Decimal(scalars[key]) for key in ('Min' + suffix, 'Max' + suffix, step))
        if delta <= 0 or minimum > maximum:
            raise ValueError(f'invalid range {suffix}')
        ranges[suffix] = {'min': str(minimum), 'max': str(maximum), 'step': str(delta),
                          'count': int((maximum - minimum) // delta) + 1}
    excluded = set(arrays['PackageExclusion'])
    return {'scope': 'strict independent config reader; not Java execution or dataset validation',
            'module_names': arrays['ModuleNames'],
            'module_counts': {name: len(entries) for name, entries in mapping.items()},
            'mapping_entries': sum(map(len, mapping.values())), 'unique_entities': len(owners),
            'duplicate_entities': {name: modules for name, modules in owners.items() if len(modules) > 1},
            'unknown_modules': sorted(set(mapping) - set(arrays['ModuleNames'])),
            'exact_exclusion_overlap': sorted(set(owners) & excluded),
            'exclusion_entries': len(arrays['PackageExclusion']),
            'exclusion_duplicates': {name: count for name, count in Counter(arrays['PackageExclusion']).items() if count > 1},
            'ranges': ranges,
            'configuration_count_decimal': prod(item['count'] for item in ranges.values()) * prod(
                len(arrays[key]) for key in ('WeightingType', 'NormalizationType', 'ThresholdType')),
            'mapping': dict(mapping)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    original = SOURCE.read_text()
    report = audit(original)
    selected = original
    for suffix, value in {'ResultsPerPage': '50', 'MNBoostFactor': '33.0', 'MDBoostFactor': '1.0'}.items():
        for prefix in ('Min', 'Max'):
            pattern = r'(' + prefix + suffix + r'\s*:\s*")[^"]+(".*)'
            selected, count = re.subn(pattern, lambda match: match[1] + value + match[2], selected)
            assert count == 1
    selected_report = audit(selected)
    assert selected_report['configuration_count_decimal'] == 1
    for key in ('mapping', 'module_names', 'mapping_entries', 'unique_entities', 'exact_exclusion_overlap'):
        assert report[key] == selected_report[key]
    (args.output / 'config-single.txt').write_text(selected)
    (args.output / 'config-single.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(keepends=True), selected.splitlines(keepends=True),
        fromfile='original-config', tofile='single-config')))
    report['single_configuration'] = selected_report['ranges']
    report['original_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report['selected_sha256'] = hashlib.sha256(selected.encode()).hexdigest()
    report['selected_is_runnable'] = 'not established; source path and entry adaptation still required'
    shutil.copy2(SOURCE, args.output / 'config-original.txt')
    shutil.copy2(__file__, args.output / 'collector.py')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'mapping'}, indent=2))


if __name__ == '__main__':
    main()
