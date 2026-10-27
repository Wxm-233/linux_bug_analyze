"""Generate conditional mathematical review relations from frozen extracted facts.

This module neither reads C nor imports the previous detector. It emits no C
assertion, patch or executable remedy. Its caller verifies the saved-input lock.
"""
from copy import deepcopy
import re

ID=re.compile(r'[A-Za-z_]\w*\Z')
LIMITS=(
    'whole_function_certified','length_contract_certified','runtime_value_proven',
    'control_flow_certified','pointer_origin_certified','full_preprocessing_certified',
    'actual_include_binding_certified','external_format_authority_certified',
    'value_range_certified',
)
API_ROLES={
    'memcpy':'argument_3_host_byte_count','memmove':'argument_3_host_byte_count',
    'skb_put':'argument_2_host_byte_count','skb_tailroom':'comparison_to_host_byte_count',
}
CONDITIONS=(
    ('actual_declaration_binding','The annotated declaration must actually bind in this version/configuration.'),
    ('field_semantic_unit','The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.'),
    ('explicit_component_meaning','The observed additive terms must have the required units and meaning; their presence does not prove completeness.'),
    ('complete_length_formula','A versioned producer/layout/consumer contract must establish every required component.'),
    ('assignment_snapshot_valid','The referenced object and its bytes must be valid at the original assignment.'),
    ('conversion_binding','The conversion spelling must bind to the expected implementation.'),
    ('consumer_binding','The API spelling and argument role must bind to the actual host-count consumer.'),
    ('count_type_representability','The mathematical decoded sum must fit the actual count type on the target configuration.'),
    ('c_arithmetic_and_conversion','C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.'),
    ('consumer_value_stability','The actual count used by each selected consumer must still equal the assignment snapshot.'),
    ('control_flow_and_reachability','The assignment and consumer must execute in the required order; lexical order alone does not prove it.'),
    ('external_contract_applicability','Any external authority must apply to this implementation and version.'),
)

def _need(condition,reason):
    if not condition:raise ValueError(reason)

def _limits(value):
    _need(isinstance(value,dict),'result must be a mapping')
    for key in LIMITS:_need(value.get(key) is False,'missing or promoted uncertified fact: '+key)
    _need(value.get('actual_path')=='unknown','actual-path proof outside this bounded stage')
    _need(value.get('normal_scope')=='local_assignment_representation_shape','unsupported upstream normal scope')
    return {**{key:False for key in LIMITS},'actual_path':'unknown'}

def _quotes(value):
    if isinstance(value,dict):
        if {'saved_path','revision','sha256','blob_sha1','start_line','end_line','text'}<=value.keys():
            yield value
        else:
            for child in value.values():yield from _quotes(child)
    elif isinstance(value,list):
        for child in value:yield from _quotes(child)

def _validate_assignment(a):
    limits=_limits(a)
    field=a.get('source_field',{})
    _need(field.get('domain') in ('le','be') and type(field.get('width')) is int and field['width'] in (16,32,64),'unsupported field domain/width')
    domain,width=field['domain'],field['width']
    _need(field.get('type')==f'__{domain}{width}','field type/domain/width conflict')
    for key in ('object','field','structure'):_need(isinstance(field.get(key),str) and ID.fullmatch(field[key]),'invalid field identity')
    _need(isinstance(a.get('variable'),str) and ID.fullmatch(a['variable']),'invalid count variable')
    _need(a.get('operator')=='=','only plain assignment supported')
    _need(a.get('conversion_implementation_certified') is False,'conversion certification outside scope')
    expected=f'{domain}{width}_to_cpu'
    if a['status']=='candidate':
        _need(a.get('representation')=='encoded_'+domain and a.get('conversion') is None,'candidate representation conflict')
    else:
        _need(a.get('representation')=='host' and a.get('conversion')==expected,'normal representation conflict')
    local=a.get('local_declaration',{})
    _need(isinstance(local.get('type'),str) and re.fullmatch(r'unsigned\s+int|unsigned|int|[us](8|16|32|64)',local['type']),'unsupported count declaration')
    _need(isinstance(a.get('rhs'),str) and a['rhs'].strip(),'missing original RHS')
    components=a.get('length_components')
    _need(isinstance(components,list) and len(components)<=1,'unsupported explicit components')
    _need(a.get('arithmetic_shape')==('field_plus_component' if components else 'field_only'),'component shape conflict')
    for c in components:
        _need(c.get('kind') in ('simple_object_macro','nonnegative_literal'),'unsupported component')
        _need(type(c.get('value')) is int and c['value']>=0,'invalid nonnegative component')
        _need(isinstance(c.get('expression'),str) and c['expression'].strip(),'missing explicit expression')
        if c['kind']=='simple_object_macro':
            _need(c.get('full_preprocessing_certified') is False and c.get('evidence'),'macro evidence missing or promoted')
    _need(a.get('evidence') and field.get('evidence') and local.get('evidence'),'missing assignment/field/local declaration evidence')
    quotes=list(_quotes(a))
    _need(quotes and len({q['revision'] for q in quotes})==1,'missing or mixed-version assignment facts')
    for q in quotes:
        _need(type(q['start_line']) is int and type(q['end_line']) is int and 0<q['start_line']<=q['end_line'],'invalid evidence lines')
        _need(re.fullmatch('[0-9a-f]{64}',q['sha256']) and re.fullmatch('[0-9a-f]{40}',q['blob_sha1']),'invalid evidence fingerprint')
        _need(isinstance(q['text'],str) and q['text'],'empty evidence')
    consumers=a.get('consumers')
    _need(isinstance(consumers,list) and consumers,'no associated consumer')
    for c in consumers:
        _need(c.get('api') in API_ROLES and c.get('role')==API_ROLES[c['api']],'unsupported consumer role')
        _need(c.get('length_expression')==a['variable'],'consumer not directly using selected local')
        _need(c.get('supported_argument_count') is True and c.get('lexical_only') is True and c.get('runtime_execution_certified') is False,'consumer scope/binding conflict')
        _need(type(c.get('begin')) is int and type(c.get('end')) is int and c['begin']<c['end'],'invalid lexical location')
        _need(isinstance(c.get('evidence'),dict) and list(_quotes(c['evidence'])),'missing consumer evidence')
    _need(a.get('first_lexical_consumer')==min(consumers,key=lambda c:c['begin']),'first lexical consumer mismatch')
    _need(a.get('first_consumer_scope')=='first visible lexical consumer; no CFG execution-order proof','unsupported first-consumer scope')
    return field,local,components,limits

def _relation(a):
    field,local,components,limits=_validate_assignment(a)
    domain,width=field['domain'],field['width']
    ref=field['object']+'->'+field['field']
    decode=dict(op='decode_unsigned_storage_snapshot',byte_order=domain,width_bits=width,
        field_reference=ref,snapshot_time='original_assignment',
        type_bound_only=[0,(1<<width)-1],actual_runtime_range_certified=False)
    terms=[dict(op='observed_nonnegative_addend',value=c['value'],expression=c['expression'],
        semantic_unit='unknown',semantic_role='unknown',required_by_complete_contract=False,
        evidence=deepcopy(c['evidence'])) for c in components]
    rhs=dict(op='add_observed_terms',base=decode,terms=terms,domain='unbounded_nonnegative_integers')
    readable=f"{a['variable']}@after_assignment == U_{domain}{width}({ref}@assignment_bytes)"
    if components:readable+=' + '+' + '.join(str(c['value']) for c in components)
    return dict(disposition='conditional_template',upstream_representation_status=a['status'],
        template_kind='local_representation_review_obligation',
        representation_obligation='normalization_required_for_review' if a['status']=='candidate' else 'matching_decode_shape_only',
        relation=dict(op='proposed_equality',lhs=dict(op='count_assignment_snapshot',variable=a['variable'],
            declared_c_type=local['type'],actual_width_and_range='unproved'),rhs=rhs,
            semantic_domain='mathematical_reference_not_C_expression',truth_at_runtime='unknown',
            normative_complete_length_formula=False),
        human_relation=readable,conversion_spelling_hint=f'{domain}{width}_to_cpu',
        conversion_hint_is_patch=False,
        applicability_conditions=[dict(name=k,requirement=v,proven=False) for k,v in CONDITIONS],
        unresolved=dict(field_unit='unknown',component_units='unknown',payload_or_total='unknown',
            required_addends='unknown',missing_addends_inferred=False,complete_length_contract='unproved'),
        observed_assignment=dict(variable=a['variable'],rhs=a['rhs'],evidence=deepcopy(a['evidence']),
            local_declaration=deepcopy(local),field=deepcopy(field),explicit_components=deepcopy(components)),
        consumer_evidence=deepcopy(a['consumers']),first_lexical_consumer=deepcopy(a['first_lexical_consumer']),
        first_consumer_scope=a['first_consumer_scope'],
        limits={**limits,'conversion_implementation_certified':False,'automatic_patch_generated':False,
            'runtime_assertion_generated':False,'pointer_offsets_certified':False,'total_length_updates_certified':False},
        limitations=['No C assertion is emitted; overflow/narrowing and real execution are not modeled.',
            'The reference uses assignment-time bytes; it must not be implemented as a later mutable-field reread.',
            'Zero or byte-symmetric inputs can satisfy a numerical equality despite an undecoded representation.',
            'The reference normalizes the observed formula only; required missing components are not inferred.'])

def generate(result):
    """Accept ONLY the frozen detector's per-query result, without outer labels."""
    records=[]
    try:limits=_limits(result)
    except ValueError as e:
        return dict(disposition='insufficient',reason=str(e),records=[],certified=False)
    if result.get('execution_status')!='ok':
        return dict(disposition='insufficient',reason=result.get('reason','upstream query insufficient'),
            records=[],limits=limits,certified=False)
    assignments=result.get('assignments')
    if not isinstance(assignments,list):
        return dict(disposition='insufficient',reason='missing assignment list',records=[],limits=limits,certified=False)
    if not assignments:
        return dict(disposition='no_eligible_assignment',reason='no upstream eligible assignment; no function correctness judgment',
            records=[],limits=limits,certified=False)
    for index,a in enumerate(assignments):
        if a.get('status') not in ('candidate','normal'):
            record=dict(disposition='refused',upstream_representation_status=a.get('status'),
                reason=a.get('reason','unsupported upstream assignment status'),
                evidence=deepcopy(a.get('evidence',[])),certified=False)
        else:
            try:record=_relation(a)
            except (ValueError,KeyError,TypeError) as e:
                record=dict(disposition='refused',upstream_representation_status=a.get('status'),
                    reason='inconsistent saved facts: '+str(e),evidence=deepcopy(a.get('evidence',[])),certified=False)
        records.append(dict(assignment_index=index,**record))
    return dict(disposition='records',function=result.get('function'),records=records,limits=limits,certified=False)
