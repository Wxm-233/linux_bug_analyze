"""Attach conditional declaration-route witnesses to saved check candidates.

This is a consistency gate for supplied documents and reviewed search roots.
It does not run a preprocessor, make, Git, a detector or a compiler.
"""
from copy import deepcopy
import hashlib,posixpath,re

ID=r'[A-Za-z_][A-Za-z_0-9]*'
UNRESOLVED=(
    'Effective compiler command, complete search order and overrides are unknown.',
    'Supplied root bindings and branch/guard applicability require review.',
    'Type definitions, conversion/API binding and actual field layout are unknown.',
    'Full length/unit/capacity, arithmetic range, value stability and runtime path remain unproved.',
    'Source hashes attest byte consistency, not external contract authority or Git authenticity.',
)
REQUIREMENTS=(
    'actual_declaration_binding','field_semantic_unit','explicit_component_meaning','complete_length_formula',
    'assignment_snapshot_valid','conversion_binding','consumer_binding','count_type_representability',
    'c_arithmetic_and_conversion','consumer_value_stability','control_flow_and_reachability','external_contract_applicability',
)
class Refusal(Exception):
    def __init__(self,code,detail):self.code=code;self.detail=detail
def need(value,code,detail):
    if not value:raise Refusal(code,detail)
def fingerprint(text):
    raw=text.encode('utf-8')
    return hashlib.sha256(raw).hexdigest(),hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def safe_path(value):
    need(isinstance(value,str) and re.fullmatch(r'[A-Za-z_0-9.+/-]+',value),'unsupported_path','only source-relative POSIX paths are supported')
    normalized=posixpath.normpath(value)
    need(not normalized.startswith('/') and normalized!='..' and not normalized.startswith('../'),'path_escape','normalized path leaves the supplied source namespace')
    return normalized
def certification_claim(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k=='proven' or k.endswith('_certified') or k.endswith('_proven'):
                if x is not False and x is not None:return k
            claim=certification_claim(x)
            if claim:return claim
    elif isinstance(v,list):
        for x in v:
            claim=certification_claim(x)
            if claim:return claim
def quotes(v):
    if isinstance(v,dict):
        if {'source_path','revision','sha256','blob_sha1','start_line','end_line','text'}<=v.keys():yield v
        else:
            for x in v.values():yield from quotes(x)
    elif isinstance(v,list):
        for x in v:yield from quotes(x)

def evaluate(payload):
    """Return conditional_candidate or insufficient; never certify a binding."""
    candidate=deepcopy(payload.get('candidate',{})) if isinstance(payload,dict) else {}
    output=dict(disposition='insufficient',upstream_candidate=candidate,upstream_is_saved_input_not_gate_verdict=True,
        source_gate=dict(level='insufficient',witnesses=[],assumptions=[],unresolved=list(UNRESOLVED)),
        requirements=[dict(name=name,proven=False) for name in REQUIREMENTS],
        check_proposal=None,reasons=[],actual_include_binding_certified=False,actual_preprocessing_certified=False,
        actual_build_certified=False,actual_layout_certified=False,complete_length_certified=False)
    try:
        need(isinstance(payload,dict),'invalid_schema','input must be an object')
        need(isinstance(payload.get('candidate'),dict),'invalid_schema','candidate must be an object')
        claim=certification_claim(payload)
        need(not claim,'unsupported_certification','input attempts to certify '+str(claim))
        need(candidate.get('status')=='candidate' and candidate.get('operator')=='=','unsupported_candidate','only a saved plain-assignment candidate is supported')
        candidate_refs=list(quotes(candidate))
        need(candidate_refs,'missing_candidate_evidence','candidate has no cited source facts')
        revision=candidate_refs[0]['revision']
        need(isinstance(revision,str) and bool(revision),'invalid_revision','revision identity is required')
        docs={}
        need(isinstance(payload.get('documents'),list),'invalid_schema','documents must be supplied explicitly')
        for d in payload['documents']:
            need(isinstance(d,dict) and isinstance(d.get('text'),str),'invalid_schema','document content must be text')
            path=safe_path(d.get('source_path'))
            need(path==d['source_path'],'unsupported_path','document identities must already be normalized')
            need(path not in docs,'duplicate_document_identity','one document per source path')
            need(d.get('revision')==revision,'mixed_revision','documents and candidate must share the exact revision')
            digest,oid=fingerprint(d['text'])
            need(d.get('sha256')==digest and d.get('blob_sha1')==oid,'document_fingerprint_mismatch',path)
            docs[path]=d
        def verify_ref(q):
            need(isinstance(q,dict),'invalid_quote','quote must be an object')
            path=safe_path(q.get('source_path'))
            need(path in docs,'missing_document',path)
            d=docs[path]
            need(q.get('revision')==revision,'mixed_revision','quote revision: '+path)
            need(q.get('sha256')==d['sha256'] and q.get('blob_sha1')==d['blob_sha1'],'quote_fingerprint_mismatch',path)
            start=q.get('start_line');end=q.get('end_line');lines=d['text'].splitlines()
            need(type(start) is int and type(end) is int and 0<start<=end<=len(lines),'invalid_quote_range',path)
            need(q.get('text')=='\n'.join(lines[start-1:end]),'quote_text_mismatch',path)
            return d
        route=payload.get('route')
        need(isinstance(route,dict),'invalid_schema','route facts are required')
        for q in [*candidate_refs,*quotes(route)]:verify_ref(q)
        source_refs=candidate.get('evidence',[])
        need(isinstance(source_refs,list) and bool(source_refs) and all(isinstance(q,dict) and {'source_path','revision','sha256','blob_sha1','start_line','end_line','text'}<=q.keys() for q in source_refs),'missing_candidate_evidence','assignment quote list required')
        source_paths={q['source_path'] for q in source_refs}
        need(len(source_paths)==1,'ambiguous_candidate_source','assignment must have a unique source document')
        include=route.get('include',{});verify_ref(include)
        need(include['source_path'] in source_paths,'include_source_mismatch','include and assignment must belong to the same source')
        match=re.fullmatch(r'\s*#\s*include\s*"([^"\n]+)"\s*',include['text'])
        need(match,'unsupported_include_syntax','one literal quoted include line required')
        token=match.group(1)
        need(token==route.get('expected_include_token'),'include_token_mismatch','complete include token differs from cited source')
        need(not token.startswith('/') and '\\' not in token,'unsupported_include_syntax','only relative POSIX literal includes are supported')
        roots=route.get('search_roots')
        need(isinstance(roots,list) and bool(roots),'missing_search_roots','explicit reviewed roots required')
        resolved=[];assumptions=[]
        for root in roots:
            need(isinstance(root,dict),'invalid_search_root','each root must be an object')
            evidence=root.get('evidence',{});verify_ref(evidence)
            expression=root.get('expression')
            need(isinstance(expression,str),'invalid_search_root','root expression required')
            need(re.search(r'(?:^|\s)-I'+re.escape(expression)+r'(?=\s|$|\))',evidence['text']),'search_root_unbacked','root flag is absent from cited text')
            variables=re.findall(r'\$\(('+ID+r')\)',expression)
            bindings=root.get('binding',{})
            need(isinstance(bindings,dict) and all(v in bindings for v in variables),'unresolved_search_root','explicit variable bindings required')
            expanded=expression
            for name in variables:expanded=expanded.replace('$('+name+')',safe_path(bindings[name]))
            need('$' not in expanded,'unsupported_search_root','Make functions are not evaluated')
            root_path=safe_path(expanded)
            assumptions_for_root=root.get('assumptions')
            need(isinstance(assumptions_for_root,list) and assumptions_for_root and all(isinstance(x,str) and x.strip() for x in assumptions_for_root),'missing_root_assumptions','bindings need explicit reviewed assumptions')
            assumptions+=assumptions_for_root
            resolved.append(dict(root_expression=expression,resolved_root=root_path,evidence=deepcopy(evidence)))
        expected_wrapper=safe_path(route.get('wrapper_source_path'))
        need(expected_wrapper in docs,'missing_document',expected_wrapper)
        primary=safe_path(posixpath.join(posixpath.dirname(include['source_path']),token))
        hits={primary} if primary in docs else set()
        for root in resolved:
            path=safe_path(posixpath.join(root['resolved_root'],token))
            root['normalized_complete_token']=path
            if path in docs:hits.add(path)
        need(expected_wrapper in hits,'header_route_disconnected','no supplied search root reaches the wrapper with the full token')
        need(hits=={expected_wrapper},'ambiguous_header_route','multiple supplied paths match the complete token: '+','.join(sorted(hits)))
        wrapper_include=route.get('wrapper_include',{});verify_ref(wrapper_include)
        need(wrapper_include['source_path']==expected_wrapper,'wrapper_source_mismatch','wrapper include must be cited in reached wrapper')
        match=re.fullmatch(r'\s*#\s*include\s*<([^>\n]+)>\s*',wrapper_include['text'])
        need(match,'unsupported_wrapper_syntax','one literal angle include required')
        wrapper_token=match.group(1)
        declaration=route.get('declaration',{});verify_ref(declaration)
        declaration_path=declaration['source_path']
        hits={safe_path(posixpath.join(root['resolved_root'],wrapper_token)) for root in resolved}
        hits={p for p in hits if p in docs}
        need(declaration_path in hits,'declaration_route_disconnected','wrapper does not reach the cited declaration in supplied roots')
        need(hits=={declaration_path},'ambiguous_declaration_route','multiple supplied declaration headers match wrapper include')
        field=candidate.get('source_field',{})
        need(isinstance(field,dict),'invalid_field_identity','source_field must be an object')
        for key in ['structure','field','object']:
            need(isinstance(field.get(key),str) and re.fullmatch(ID,field[key]),'invalid_field_identity',key)
        dtype=field.get('type');domain=field.get('domain');width=field.get('width')
        need(domain in ('be','le') and type(width) is int and width in (16,32,64) and dtype=='__'+domain+str(width),'declaration_identity_mismatch','annotation/domain/width disagree')
        need(candidate.get('representation')=='encoded_'+domain and candidate.get('conversion') is None,'unsupported_candidate','only raw encoded field candidate supported')
        text=declaration['text']
        need(not any(x in text for x in ['/*','//','#']),'unsupported_declaration_syntax','macro/comment context not resolved')
        pattern=r'\s*struct\s+'+re.escape(field['structure'])+r'\s*\{([^{}]*)\}\s*(?:__attribute__\s*\(\(\s*packed\s*\)\)|__packed)?\s*;\s*'
        match=re.fullmatch(pattern,text)
        need(match,'declaration_identity_mismatch','one matching direct struct declaration required')
        members=[]
        for item in match.group(1).split(';'):
            m=re.fullmatch(r'\s*(__[bl]e(?:16|32|64))\s+('+ID+r')\s*',item)
            if m and m.group(2)==field['field']:members.append(m.group(1))
        need(members==[dtype],'declaration_identity_mismatch','field/type not uniquely present in matching struct')
        field_refs=list(quotes(field))
        member_refs=[q for q in field_refs if q['source_path']==declaration_path and declaration['start_line']<=q['start_line']<=q['end_line']<=declaration['end_line']]
        need(any(re.fullmatch(r'\s*'+re.escape(dtype)+r'\s+'+re.escape(field['field'])+r'\s*;\s*',q['text']) for q in member_refs),'declaration_identity_mismatch','candidate member quote must lie in reached declaration')
        need(any(q['source_path'] in source_paths and re.search(r'\bstruct\s+'+re.escape(field['structure'])+r'\s*\*\s*'+re.escape(field['object'])+r'\b',q['text']) for q in field_refs),'object_declaration_mismatch','object declaration quote not linked to candidate source')
        variable=candidate.get('variable');rhs=candidate.get('rhs')
        need(isinstance(variable,str) and re.fullmatch(ID,variable) and isinstance(rhs,str),'invalid_candidate_identity','count and original RHS required')
        need(any(re.fullmatch(r'\s*'+re.escape(variable)+r'\s*=\s*'+re.escape(rhs)+r'\s*;\s*',q['text']) for q in source_refs),'candidate_assignment_mismatch','original assignment must match cited source')
        need(not re.search(r'\b(?:be|le)(?:16|32|64)_to_cpu\s*\(',rhs),'candidate_representation_conflict','visible decoder conflicts with raw candidate metadata')
        need(re.search(r'\b'+re.escape(field['object'])+r'\s*->\s*'+re.escape(field['field'])+r'\b',rhs),'candidate_field_mismatch','raw source field not present in RHS')
        output.update(disposition='conditional_candidate',check_proposal=dict(kind='representation_normalization_review',
            field=field['structure']+'.'+field['field'],annotation=dtype,conversion_spelling=domain+str(width)+'_to_cpu',
            scope='review normalization before upstream host-count consumers; full length/capacity and conversion binding remain separate'))
        output['source_gate'].update(level='conditional_static_source_route',revision=revision,
            witnesses=[deepcopy(include),deepcopy(wrapper_include),deepcopy(declaration),*resolved],
            assumptions=list(dict.fromkeys(assumptions)),known_supplied_header_hits=sorted({expected_wrapper}),
            missing_in_registry_is_proven_absence=False)
    except Refusal as error:
        output['reasons'].append(dict(code=error.code,detail=error.detail))
    return output
