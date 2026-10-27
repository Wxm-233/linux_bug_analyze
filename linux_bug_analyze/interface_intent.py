"""Preserve an externally registered interface question before evaluation.

This checks structured declarations, not natural-language meaning or source
semantics. The trusted intent is supplied separately from a model candidate.
Matching it does not establish authority, object identity or temporal stability.
"""
from __future__ import annotations

import json
from typing import Any

from .contract_protocol import ContractError, evaluate_contract, validate_contract


def _canonical(node: dict[str, Any], bindings: dict[str, str]) -> Any:
    if 'symbol' in node:
        return ('symbol', bindings[node['symbol']])
    if 'literal' in node:
        # Include type: Python otherwise equates True and 1.
        value = node['literal']
        return ('literal', type(value).__name__, json.dumps(value, sort_keys=True))
    args = [_canonical(arg, bindings) for arg in node['args']]
    if node['op'] in {'eq', 'ne', 'and', 'or'}:
        args.sort(key=repr)
    return (node['op'], tuple(args))


def check_intent(intent: dict, candidate: dict) -> dict:
    """Check alpha-renaming/commutative equivalence in the existing finite DSL.

    Other algebraically equivalent rewrites are not decided here. A mismatch
    denotes failure to match this registered question, not an invalid theorem.
    Symbol-role declarations remain external inputs, not proven data bindings.
    """
    result = {'intent_status': 'insufficient', 'reason': '',
              'semantic_authority_established': False, 'evidence_established': False}
    try:
        if not isinstance(intent, dict) or intent.get('schema') != 'interface_intent_v1':
            raise ValueError('invalid registered intent')
        if not isinstance(intent.get('interface_id'), str) or not intent['interface_id']:
            raise ValueError('missing interface identity')
        if not isinstance(intent.get('deadline_event'), str) or not intent['deadline_event']:
            raise ValueError('missing registered consumer event')
        baseline = intent['contract']
        validate_contract(baseline)
        if not isinstance(candidate, dict):
            raise ValueError('invalid candidate')
        if candidate.get('interface_id') != intent['interface_id']:
            raise ValueError('interface identity changed')
        if candidate.get('deadline_event') != intent['deadline_event']:
            raise ValueError('consumer deadline changed')
        proposed = candidate['contract']
        validate_contract(proposed)
        if proposed['revision'] != baseline['revision']:
            raise ValueError('revision changed')
        bindings = candidate['symbol_bindings']
        if not isinstance(bindings, dict) or set(bindings) != set(proposed['symbols']):
            raise ValueError('incomplete symbol-role bindings')
        if (not all(isinstance(v, str) for v in bindings.values())
                or set(bindings.values()) != set(baseline['symbols'])
                or len(bindings) != len(set(bindings.values()))):
            raise ValueError('missing or aliased semantic role')
        for name, role in bindings.items():
            if proposed['symbols'][name] != baseline['symbols'][role]:
                raise ValueError('symbol type/role changed')
        identity = {name: name for name in baseline['symbols']}
        for field in ('scope', 'relation'):
            if _canonical(proposed[field], bindings) != _canonical(baseline[field], identity):
                raise ValueError(field+' does not match registered intent')
        result.update(intent_status='matches_registered_intent',
                      reason='Structured question preserved only; original evidence review remains required.')
    except (ContractError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result['reason'] = str(exc)
    return result


def evaluate_with_intent(intent: dict, candidate: dict, ledger: dict, record: dict) -> dict:
    """Compose the intent guard with the unchanged contract evaluator.

    No missing facts or supported claims are invented. In particular a later
    sample cannot become the required consumption reference through this guard.
    """
    guard = check_intent(intent, candidate)
    blocked = {'applicability': 'insufficient', 'relation_at_observation': 'insufficient',
               'relation_at_deadline': 'insufficient', 'whole_path': 'insufficient'}
    if guard['intent_status'] != 'matches_registered_intent':
        return {'intent': guard, 'core_executed': False, 'evaluation': blocked}
    if not isinstance(record, dict) or record.get('deadline_event') != intent['deadline_event']:
        guard.update(intent_status='insufficient', reason='record deadline differs from registered consumer')
        return {'intent': guard, 'core_executed': False, 'evaluation': blocked}
    return {'intent': guard, 'core_executed': True,
            'evaluation': evaluate_contract(candidate['contract'], ledger, record)}
