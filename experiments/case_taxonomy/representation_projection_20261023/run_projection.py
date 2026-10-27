"""Known-development integration; selected source sites and premises are external."""
from pathlib import Path
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from linux_bug_analyze.contract_protocol import CLAIM_ROLES, SCHEMA, evaluate_contract
from linux_bug_analyze.representation_semantics import analyze_representation
from linux_bug_analyze.representation_source import extract_representation_predicate


def bridge(query, host, projection, packet):
    """Register reviewed local premises, not a newly discovered normative rule."""
    context = query['id'] + '.' + host
    object_id = context + '.selected_field'
    sample_event = context + '.generated_scalar_evaluation'
    deadline = context + '.conditional_source_read_not_observed'
    origins = {k: 'researcher_authored' for k in
               ('scope', 'relation', 'symbols', 'required_claims', 'authority_kind')}
    contract = {
        'schema': SCHEMA, 'id': context + '.predicate', 'revision': packet['revision'],
        'authority_kind': 'consumer_inferred', 'sufficient_for_correctness': False,
        'field_origins': origins,
        'required_claims': {r: 'review.' + r for r in CLAIM_ROLES},
        'symbols': {'local_model_selected': {'type': 'bool', 'role': 'configuration'},
                    'actual': {'type': 'bool', 'role': 'observation'},
                    'reference': {'type': 'bool', 'role': 'observation'}},
        'scope': {'symbol': 'local_model_selected'},
        'relation': {'op': 'eq', 'args': [{'symbol': 'actual'}, {'symbol': 'reference'}]},
    }
    expr = query['expression_source']
    decl = query['declaration_source']
    docs = {name: {'context_revision': packet['revision'], 'path': source['path'],
                   'start_line': source['start_line'], 'end_line': source['end_line']}
            for name, source in [('expression', expr), ('declaration', decl)]}
    refs = [{'document': k, 'start_line': v['start_line'], 'end_line': v['end_line']}
            for k, v in docs.items()]
    claims = {'review.' + role: {
        'role': role, 'status': 'supported', 'origin': 'researcher_review',
        'context_id': context, 'references': copy.deepcopy(refs),
        'statement': ('External local representation/use premise under the declared unsigned model; '
                      'not a proof of effective C configuration, valid inode, or reachable runtime.')}
        for role in CLAIM_ROLES}
    claims['review.authority'].update(authority_kind='consumer_inferred',
                                      supports_requirement='review.consumer_requirement')
    for role, key in [('applicability', 'scope'), ('consumer_requirement', 'relation')]:
        claims['review.' + role].update(expression=copy.deepcopy(contract[key]),
                                        symbols=copy.deepcopy(contract['symbols']))
    for role in ['consumer_requirement', 'provider_binding', 'object_binding', 'deadline_binding']:
        claims['review.' + role]['object_id'] = object_id
    claims['review.deadline_binding'].update(event_id=deadline, event_kind='content_consumption')
    binding = {'object_id': object_id, 'event_id': sample_event, 'deadline_id': deadline}
    claims['review.observation'] = {
        'role': 'observation_binding', 'status': 'supported', 'origin': 'researcher_review',
        'context_id': context, 'references': copy.deepcopy(refs),
        'statement': 'Generated scalar projection is a separate sample, never actual source consumption.',
        'binding': {**binding, 'context_id': context, 'event_kind': 'sample'},
    }
    record = {'id': context, 'revision': packet['revision'], 'basis': 'synthetic',
              'context_id': context, 'object_id': object_id, 'sample_event': sample_event,
              'deadline_event': deadline, 'sample_kind': 'sample',
              'observation_binding': {**binding, 'claim': 'review.observation'}, 'facts': {}}
    values = {'local_model_selected': True, 'actual': projection['sample']['actual'],
              'reference': projection['sample']['expected']}
    for name, value in values.items():
        role = contract['symbols'][name]['role']
        fact = {'value': value, 'claim': 'fact.' + name}
        typed = {'symbol': name, 'value': value, 'role': role, 'context_id': context}
        if role == 'observation':
            fact.update(object_id=object_id, event_id=sample_event)
            typed.update(object_id=object_id, event_id=sample_event)
        claims['fact.' + name] = {
            'role': 'fact', 'status': 'supported', 'context_id': context,
            'origin': 'synthetic_assumption' if role == 'configuration' else 'program_projection',
            'statement': ('Explicit local-model assumption, not actual Kconfig.' if role == 'configuration'
                          else 'Value computed by the registered generic representation projector.'),
            'references': copy.deepcopy(refs), 'fact': typed,
        }
        record['facts'][name] = fact
    ledger = {'revision': packet['revision'], 'basis': 'synthetic', 'context_id': context,
              'contract_id': contract['id'], 'field_origins': copy.deepcopy(origins),
              'documents': docs, 'claims': claims}
    return contract, ledger, record


def execute():
    packet = json.loads((HERE / 'inputs_pre.json').read_text(encoding='utf-8'))
    source_lines = {}
    for rel, source in packet['source_files'].items():
        raw = (ROOT / source['artifact']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('source identity changed: ' + rel)
        source_lines[rel] = raw.decode('utf-8-sig').splitlines()
    for query in packet['queries']:
        expr, decl = query['expression_source'], query['declaration_source']
        site = '\n'.join(source_lines[expr['path']][expr['start_line'] - 1:expr['end_line']])
        member = '\n'.join(source_lines[decl['path']][decl['start_line'] - 1:decl['end_line']])
        if site != expr['full_site'] or site.count(query['expression']) != 1:
            raise ValueError('selected expression is not the registered source occurrence: ' + query['id'])
        if member != query['declaration']:
            raise ValueError('selected declaration differs from source: ' + query['id'])
    records, base = [], None
    for query in packet['queries']:
        extraction = extract_representation_predicate(
            query['expression'], field_ref=query['field_ref'], declaration=query['declaration'],
            constants=packet['constants'], conversion_registry=packet['conversion_registry'])
        for host in packet['host_conditions']:
            row = {'id': query['id'] + '.' + host, 'host_condition': host,
                   'basis': 'real source syntax plus generated unsigned scalar projection',
                   'source_extraction': copy.deepcopy(extraction)}
            if extraction['status'] != 'extracted':
                row.update(projection={'status': 'insufficient', 'reason': extraction['reason']},
                           core_evaluation=None)
            else:
                spec = {**extraction['spec_partial'], 'host_endian': host}
                projection = analyze_representation(spec)
                row.update(spec=spec, projection=projection, core_evaluation=None)
                if projection['status'] != 'insufficient':
                    contract, ledger, record = bridge(query, host, projection, packet)
                    row['core_input'] = {'contract': contract, 'ledger': ledger, 'record': record}
                    row['core_evaluation'] = evaluate_contract(contract, ledger, record, allow_synthetic=True)
                    if base is None:
                        base = (contract, ledger, record)
            records.append(row)
    controls = []
    if base is not None:
        for kind in ['missing_authority', 'wrong_fact_object', 'unreviewed_sample_promotion']:
            contract, ledger, record = copy.deepcopy(base)
            if kind == 'missing_authority':
                del ledger['claims']['review.authority']
            elif kind == 'wrong_fact_object':
                record['facts']['actual']['object_id'] = 'unrelated_object'
            else:
                record['sample_event'] = record['deadline_event']
                record['sample_kind'] = 'content_consumption'
                record['observation_binding']['event_id'] = record['deadline_event']
                for key in ['actual', 'reference']:
                    record['facts'][key]['event_id'] = record['deadline_event']
            controls.append({'id': kind, 'kind': 'constructed_evidence_control',
                             'evaluation': evaluate_contract(contract, ledger, record, allow_synthetic=True)})
    return {'records': records, 'controls': controls,
            'scope': 'known-case local method development; no new case or runtime observation'}


if __name__ == '__main__':
    print(json.dumps(execute(), ensure_ascii=False, indent=2))
