"""Typed role checks and lossless conjunction inspection of model candidates.

Diagnostics operate on externally supplied observed values, never approve model
semantics, and never replace an absent deadline reference with a nearby sample.
"""
import copy

from .contract_protocol import validate_contract, _expression, _value_type


def _symbols(node):
    if 'symbol' in node:
        return {node['symbol']}
    return set().union(*(_symbols(x) for x in node.get('args', [])))


def _leaves(node, path):
    # Only conjunction is separable into necessary obligations. Never split OR.
    if node.get('op') == 'and':
        return [row for i,arg in enumerate(node['args'])
                for row in _leaves(arg, path+['args',i])]
    return [(path,node)]


def _at(tree,path):
    for item in path:
        tree=tree[item]
    return tree


def inspect_parts(candidate, role_registry, facts, *, context_id):
    """Return all clauses and typed dependencies without modifying the input.

    role_registry is reviewed interface vocabulary, not inferred from variable
    names. facts are trusted adapter output (no model-generated facts accepted).
    Local value results are diagnostic even if the overall scope is inadmissible.
    """
    contract=candidate['contract']
    validate_contract(contract)
    bindings=candidate.get('symbol_bindings', {})
    issues=[]; per_symbol={}; role_users={}
    if not isinstance(bindings,dict) or set(bindings)!=set(contract['symbols']):
        issues.append('incomplete bindings')
        bindings=bindings if isinstance(bindings,dict) else {}
    for name,spec in contract['symbols'].items():
        role=bindings.get(name)
        definition=role_registry.get(role) if isinstance(role,str) else None
        errors=[]
        if definition is None:
            errors.append('unknown semantic role')
        else:
            if spec!={k:definition[k] for k in ('type','role')}:
                errors.append('type/category mismatch')
            role_users.setdefault(role,[]).append(name)
        per_symbol[name]=dict(semantic_role=role,declared=copy.deepcopy(spec),issues=errors)
    for role,names in role_users.items():
        if len(names)>1:
            for name in names:per_symbol[name]['issues'].append('multiple variables assigned to one role')
    for name,row in per_symbol.items():
        issues.extend(name+': '+reason for reason in row['issues'])
    parts=[]
    for field in ('scope','relation'):
        for path,node in _leaves(contract[field],[field]):
            used=sorted(_symbols(node)); values={}; missing=[]
            for name in used:
                binding=per_symbol[name];role=binding['semantic_role']
                if binding['issues']:
                    missing.append(dict(symbol=name,reason='invalid role binding'));continue
                fact=facts.get(role)
                if not isinstance(fact,dict):
                    missing.append(dict(symbol=name,reason='no registered fact'));continue
                if (fact.get('origin')!='program_projection' or fact.get('context_id')!=context_id
                        or not isinstance(fact.get('evidence'),list) or not fact['evidence']):
                    missing.append(dict(symbol=name,reason='untrusted or different-context fact'));continue
                try:value_type=_value_type(fact.get('value'))
                except ValueError:
                    missing.append(dict(symbol=name,reason='invalid fact value'));continue
                if value_type!=contract['symbols'][name]['type']:
                    missing.append(dict(symbol=name,reason='fact type mismatch'));continue
                values[name]=fact['value']
            decision='insufficient' if missing else ('satisfied' if _expression(node,values) else 'violated')
            parts.append(dict(field=field,path=path,expression=copy.deepcopy(node),
                symbols=used,semantic_roles=[per_symbol[n]['semantic_role'] for n in used],
                fact_bindings={n:copy.deepcopy(facts[per_symbol[n]['semantic_role']]) for n in values},
                missing=missing,local_value_relation=decision,
                semantic_authority_established=False))
    for row in parts:
        assert _at(contract,row['path'])==row['expression']
    summary={field:{s:sum(r['field']==field and r['local_value_relation']==s for r in parts)
                    for s in ('satisfied','violated','insufficient')} for field in ('scope','relation')}
    return dict(binding_status='insufficient' if issues else 'typed_bindings_valid',binding_issues=issues,
        symbol_checks=per_symbol,parts=parts,summary=summary,
        original_scope=copy.deepcopy(contract['scope']),original_relation=copy.deepcopy(contract['relation']),
        decomposition='all conjunction leaves retained with original paths; OR/NOT stay intact',
        interpretation='Local value diagnostics only; no candidate clause is removed or approved.',
        relation_at_deadline='insufficient',whole_path='insufficient')
