"""Record import compatibility without loading a model or allowing network connects."""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import socket
import sys
import traceback


def deny_connection(*args, **kwargs):
    raise RuntimeError('network disabled for import-only probe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('output already exists')
    socket.socket.connect = deny_connection
    socket.socket.connect_ex = deny_connection
    report = {'python': platform.python_version(), 'executable': sys.executable,
              'sys_path': sys.path, 'packages': {dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()},
              'model_loads': 0, 'inferences': 0, 'network_connects_disabled': True, 'imports': []}
    for name in ('torch', 'transformers', 'hanlp', 'hanlp.components.mtl.multi_task_learning', 'hanlp.components.mtl.tasks.srl.rank_srl'):
        try:
            module = importlib.import_module(name)
            path = Path(module.__file__)
            report['imports'].append({'module': name, 'success': True, 'path': str(path),
                                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        except Exception:
            report['imports'].append({'module': name, 'success': False, 'traceback': traceback.format_exc()})
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{key: value for key, value in row.items() if key != 'traceback'} for row in report['imports']], indent=2))
    if not all(row['success'] for row in report['imports']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
