"""Load pinned local HanLP assets and preserve raw SRL outputs, without field mapping."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import re
import shutil
import socket
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--assets-run', required=True)
    parser.add_argument('--allow-unused-ner-buffers', action='store_true')
    parser.add_argument('--protocol', default='research/protocols/hanlp-srl-smoke-v1.json')
    args = parser.parse_args()
    if any(not re.fullmatch('[A-Za-z0-9_-]+', value) for value in (args.run_id, args.assets_run)):
        raise ValueError('invalid ID')
    folder = ROOT / 'research/evidence/runs' / args.run_id
    folder.mkdir()
    protocol = ROOT / args.protocol
    plan = json.loads(protocol.read_text())
    shutil.copy2(protocol, folder / 'protocol.json')
    shutil.copy2(__file__, folder / 'runner.py')
    compatibility = None
    if args.allow_unused_ner_buffers:
        amendment = ROOT / 'research/protocols/hanlp-ner-buffer-compat-v1.json'
        shutil.copy2(amendment, folder / 'compatibility.json')
        compatibility = json.loads(amendment.read_text())
    report = {'success': False, 'model_loaded': False, 'inference_passes': 0, 'field_accuracy_measured': False}
    started = time.monotonic()
    try:
        source = ROOT / plan['input']
        parent = json.loads((source.parent / 'report.json').read_text())
        if sha(source) != parent['artifact_sha256'][source.name]:
            raise ValueError('frozen input changed')
        inputs = [{'id': row['id'], 'text': row['text']} for row in json.loads(source.read_text())]
        (folder / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
        assets_report = ROOT / 'research/evidence/runs' / args.assets_run / 'report.json'
        assets = json.loads(assets_report.read_text())
        if not assets['success']:
            raise ValueError('incomplete assets')
        originals = ROOT / 'research/evidence/originals' / args.assets_run
        directories = {}
        for resource in assets['resources']:
            identity = resource['id']
            if sha(originals / f'{identity}.zip') != resource['sha256']:
                raise ValueError('archive changed')
            destination = originals / identity
            for relative, digest in resource['files'].items():
                if sha(destination / relative) != digest:
                    raise ValueError(f'asset changed: {relative}')
            configs = list(destination.rglob('config.json'))
            if len(configs) != 1:
                raise ValueError('ambiguous model config')
            directories[identity] = str(configs[0].parent)
        os.environ.update({'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false', 'CUDA_VISIBLE_DEVICES': '', 'HANLP_HOME': str(ROOT / '.build/hanlp-offline-cache')})
        network_attempts = []

        def deny_connection(*args, **kwargs):
            network_attempts.append(repr(args[1:]))
            raise RuntimeError('network disabled: unarchived resource requested')

        socket.socket.connect = deny_connection
        socket.socket.connect_ex = deny_connection
        import torch
        import hanlp
        from hanlp.layers.transformers import resource as resource_module
        random.seed(0)
        torch.manual_seed(0)
        torch.set_num_threads(4)
        original_load = torch.load
        load_events = []
        original_state_load = torch.nn.Module.load_state_dict
        state_events = []

        def safe_load(*values, **options):
            if options.get('weights_only') is False or options.get('pickle_module') is not None:
                raise ValueError('unsafe deserialization requested')
            options['weights_only'] = True
            load_events.append(str(values[0]) if values else str(options.get('f')))
            return original_load(*values, **options)

        torch.load = safe_load

        def checked_state_load(module, *values, **options):
            result = original_state_load(module, *values, **options)
            event = {'class': type(module).__name__, 'missing': list(result.missing_keys), 'unexpected': list(result.unexpected_keys)}
            state_events.append(event)
            if event['missing'] or event['unexpected']:
                if not compatibility or event['unexpected'] or set(event['missing']) != set(compatibility['allowed_missing']):
                    raise ValueError('partial checkpoint loading rejected')
                from hanlp.layers.transformers.relative_transformer import RelativeSinusoidalPositionalEmbedding
                parameters = dict(module.named_parameters())
                buffers = dict(module.named_buffers())
                verified = []
                for name in event['missing']:
                    if name in parameters or name not in buffers:
                        raise ValueError('missing object is not a buffer')
                    owner = module.get_submodule(name.rsplit('.', 1)[0])
                    if type(owner) is not RelativeSinusoidalPositionalEmbedding:
                        raise ValueError('wrong buffer owner')
                    rebuilt = RelativeSinusoidalPositionalEmbedding(owner.embedding_dim, owner.padding_idx, owner.weights.shape[0] - 1)
                    if not torch.equal(owner.weights.cpu(), rebuilt.weights):
                        raise ValueError('positional buffer differs from deterministic reconstruction')
                    verified.append({'key': name, 'shape': list(owner.weights.shape), 'reconstruction_exact': True})
                event['verified_unused_buffers'] = verified
            return result

        torch.nn.Module.load_state_dict = checked_state_load
        resource_module.tokenizer_mirrors['mMiniLMv2L6-no-space'] = directories['tokenizer']
        resource_module.model_mirrors['mMiniLMv2L6-no-space'] = directories['encoder']
        manifest = {'source_sha256': sha(source), 'assets_report_sha256': sha(assets_report),
                    'packages': {dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()},
                    'directories': directories, 'torch_threads': torch.get_num_threads(),
                    'source_built_dependency': 'hanlp-common0.0.24 fixed official commit; see environment-01'}
        (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        try:
            component = hanlp.load(directories['mtl'], devices=-1, verbose=False, trust_remote_code=False)
            report['model_loaded'] = True
            report['resolved_tasks'] = component.resolve_tasks('srl', None)
            if compatibility:
                if any('ner' in group for group in report['resolved_tasks']):
                    raise ValueError('NER in execution plan')

                def reject_ner(*values):
                    raise RuntimeError('unexpected execution of compatibility-excluded NER decoder')

                component.model_.decoders['ner'].register_forward_pre_hook(reject_ner)
                report['ner_execution_guard'] = True
            texts = [row['text'] for row in inputs]
            for repeat in (1, 2):
                batches = []
                for start in range(0, len(texts), 4):
                    with torch.inference_mode():
                        output = component(texts[start:start+4], tasks='srl')
                    batches.append({'ids': [row['id'] for row in inputs[start:start+4]],
                                    'output': json.loads(output.to_json())})
                    (folder / f'raw-{repeat}-batch-{start//4}.json').write_text(output.to_json() + '\n')
                (folder / f'raw-{repeat}.json').write_text(json.dumps(batches, indent=2) + '\n')
                report['inference_passes'] += 1
            report['repeat_identical'] = (folder / 'raw-1.json').read_bytes() == (folder / 'raw-2.json').read_bytes()
            report['success'] = True
        finally:
            report['network_attempts'] = network_attempts
            report['weight_loads'] = load_events
            report['state_dict_loads'] = state_events
    except Exception:
        report['failure'] = traceback.format_exc()
    report['elapsed_seconds'] = time.monotonic() - started
    report['artifact_sha256'] = {path.name: sha(path) for path in sorted(folder.iterdir()) if path.is_file()}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
