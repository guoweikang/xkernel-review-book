"""Validate declared contract structure and source identity, never behavior truth."""

import hashlib


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), 'invalid fields')


def words(value):
    require(isinstance(value, str) and bool(value.strip()), 'empty text')


def validate(contract, registry, root):
    keys(contract, ['schema', 'entity', 'revision', 'source_sha256', 'configuration',
                    'responsibility', 'kind', 'conditions', 'effect'])
    require(contract['schema'] == 'crate-contract/0', 'unsupported schema')
    identity = contract['entity']
    require(isinstance(identity, str) and identity in registry, 'unknown entity')
    binding = registry[identity]
    require(contract['revision'] == binding['revision'], 'revision mismatch')
    source = root / binding['source']
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    require(contract['source_sha256'] == binding['sha256'] == digest, 'source mismatch')
    keys(contract['configuration'], ['status', 'expression'])
    configuration = contract['configuration']
    require(configuration['status'] in ('unknown', 'declared'), 'invalid configuration status')
    if configuration['status'] == 'unknown':
        require(configuration['expression'] is None, 'unknown configuration must be null')
    else:
        words(configuration['expression'])
    keys(contract['responsibility'], ['owner', 'basis'])
    words(contract['responsibility']['owner'])
    require(contract['responsibility']['basis'] == 'declared', 'owner is not verified')
    require(isinstance(contract['conditions'], list), 'missing conditions')
    for condition in contract['conditions']:
        keys(condition, ['subject', 'operator', 'value'])
        words(condition['subject'])
        require(condition['operator'] in ('eq', 'ne', 'gt', 'le'), 'unsupported operator')
        require(type(condition['value']) in (str, int, bool), 'invalid value')
        if condition['operator'] in ('gt', 'le'):
            require(type(condition['value']) is int, 'ordering requires integer')
    effect = contract['effect']
    if contract['kind'] == 'field_update':
        keys(effect, ['replace', 'preserve', 'result'])
        for field in ('replace', 'preserve'):
            require(isinstance(effect[field], list) and bool(effect[field]), 'missing field roles')
            for value in effect[field]:
                words(value)
            require(len(set(effect[field])) == len(effect[field]), 'duplicate field')
        require(not set(effect['replace']) & set(effect['preserve']), 'conflicting field roles')
        require(effect['result'] == 'new_value', 'unsupported result')
    elif contract['kind'] == 'callback':
        keys(effect, ['target', 'count', 'payload', 'after', 'on_collection_failure'])
        words(effect['target'])
        require(type(effect['count']) is int and effect['count'] >= 0, 'invalid callback count')
        require(effect['payload'] in ('whole', 'fragment'), 'invalid payload')
        require(effect['after'] in ('whole_collection', 'each_fragment'), 'invalid ordering')
        require(effect['on_collection_failure'] in ('no_callback', 'prior_callbacks_possible'), 'invalid failure boundary')
    else:
        raise ValueError('unsupported contract kind')
    return {'structure': 'valid', 'source_identity': 'matched', 'behavior': 'unverified',
            'ownership': 'declared_only', 'sharing': 'unknown',
            'configuration': configuration['status']}
