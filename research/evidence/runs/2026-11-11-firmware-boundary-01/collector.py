"""Archive a retrospective firmware boundary case without changing the kernel."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib


CHANGE = '20c6ead060376cf628b9ba3fcbb60fd8ad64e44a'
PATHS = (
    'drivers/firmware/of/Cargo.toml',
    'drivers/firmware/of/src/lib.rs',
    'drivers/firmware/of/docs/design.md',
    'drivers/firmware/of/docs/firmware-node-direction.md',
    'drivers/firmware/rs-fdtree/Cargo.toml',
    'drivers/firmware/rs-fdtree/docs/design.md',
    'drivers/firmware/rs-fdtree/src/cpu.rs',
    'drivers/firmware/rs-fdtree/src/fwnode_backend/dtb.rs',
    'drivers/firmware/rs-fdtree/tests/tests_fwnode.rs',
)
MARKERS = {
    'cpu_classification_literal': 'node.property_str("device_type") == Some("cpu")',
    'cpu_view_classification': 'CpuNode::from_node(node).is_some()',
    'cpu_view_identity': 'CpuNode::from_node(node)?.hardware_id().ok().flatten()',
    'address_cells_default': 'node.parent_property_u32("#address-cells").unwrap_or(1)',
    'node_reg_call_or_definition': 'node_reg(',
    'cpu_enabled_policy': 'pub fn is_enabled_cpu_node',
}


def git(repo, *arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments])


def locate(source):
    return {name: [number for number, line in enumerate(source.splitlines(), 1)
                   if marker in line] for name, marker in MARKERS.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--current', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    revisions = {
        'before': git(args.repo, 'rev-parse', CHANGE + '^').decode().strip(),
        'after': git(args.repo, 'rev-parse', CHANGE).decode().strip(),
        'current': git(args.repo, 'rev-parse', args.current + '^{commit}').decode().strip(),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'kind': 'retrospective_development_case', 'revisions': revisions,
              'selection': 'Selected after reading the historical patch; not blind evaluation',
              'kernel_tests_run': False, 'resolved_call_graph': False,
              'semantic_classifier': False, 'snapshots': {}}
    for label, revision in revisions.items():
        tracked = set(git(args.repo, 'ls-tree', '-r', '--name-only', revision)
                      .decode().splitlines())
        snapshot = {'files': [], 'missing': []}
        for relative in PATHS:
            if relative not in tracked:
                snapshot['missing'].append(relative)
                continue
            content = git(args.repo, 'show', f'{revision}:{relative}')
            destination = args.output / label / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            snapshot['files'].append({'path': relative, 'bytes': len(content),
                                      'sha256': hashlib.sha256(content).hexdigest()})
            if relative == 'drivers/firmware/of/src/lib.rs':
                snapshot['of_literal_markers'] = locate(content.decode())
            if relative == 'drivers/firmware/of/Cargo.toml':
                snapshot['of_declared_dependencies'] = tomllib.loads(content.decode()).get('dependencies', {})
        report['snapshots'][label] = snapshot
    before = report['snapshots']['before']
    after = report['snapshots']['after']
    report['of_dependency_declarations_equal_before_after'] = (
        before['of_declared_dependencies'] == after['of_declared_dependencies'])
    patch = git(args.repo, 'show', '--format=fuller', CHANGE, '--', *PATHS)
    (args.output / 'historical.patch').write_bytes(patch)
    report['patch_sha256'] = hashlib.sha256(patch).hexdigest()
    report['collector_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output / 'collector.py').write_bytes(Path(__file__).read_bytes())
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'revisions': revisions, 'dependency_declarations_equal':
                      report['of_dependency_declarations_equal_before_after'],
                      'markers_before': before['of_literal_markers'],
                      'markers_after': after['of_literal_markers']}, indent=2))


if __name__ == '__main__':
    main()
