"""Bounded syntax/layout facts from an already-read producer and consumer.

No preprocessing, C execution, external authority or actual ABI certification.
Opaque macro/typed-store widths stay opaque; no conventional values are inserted.
"""
from pathlib import Path
import ast,hashlib,re

ID=r'[A-Za-z_]\w*'
NONCODE=re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
def mask(text):
    return NONCODE.sub(lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),text)
def need(value,reason):
    if not value:raise ValueError(reason)
def unwrap(text):
    text=text.strip()
    while text.startswith('(') and closing(text,0,'(',')')==len(text)-1:text=text[1:-1].strip()
    return text
def closing(text,start,left,right):
    level=0
    for i in range(start,len(text)):
        if text[i]==left:level+=1
        elif text[i]==right:
            level-=1
            if not level:return i
    raise ValueError('unbalanced syntax')
def split_args(text):
    result=[];level=0;start=0
    for i,c in enumerate(text):
        if c in '([':level+=1
        elif c in ')]':level-=1
        elif c==',' and level==0:result.append(text[start:i].strip());start=i+1
    result.append(text[start:].strip());return result

class Source:
    def __init__(self,record):
        self.meta=record;self.raw=Path(record['saved_path']).read_bytes()
        need(hashlib.sha256(self.raw).hexdigest()==record['sha256'],'saved bytes changed')
        need(hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest()==record['blob_sha1'],'blob changed')
        self.text=self.raw.decode('utf-8');self.code=mask(self.text)
    def cite(self,start,end):
        first=self.text.count('\n',0,start)+1;last=self.text.count('\n',0,max(start,end-1))+1
        lines=self.text.splitlines()
        return {**{k:self.meta[k] for k in ['revision','source_path','saved_path','sha256','blob_sha1']},
            'start_line':first,'end_line':last,'text':'\n'.join(lines[first-1:last])}

def functions(source):
    result=[]
    for m in re.finditer(rf'\b(?P<name>{ID})\s*\((?P<args>[^;{{}}]*?)\)\s*\{{',source.code):
        if m['name'] in ('if','for','while','switch'):continue
        if source.code[:m.start()].count('{')!=source.code[:m.start()].count('}'):continue
        brace=m.end()-1;end=closing(source.code,brace,'{','}')+1
        result.append(dict(name=m['name'],args=split_args(m['args']),start=m.start(),body=brace+1,end=end))
    return result

def calls(source,scope,name):
    result=[]
    for m in re.finditer(rf'\b{re.escape(name)}\s*\(',source.code[scope['body']:scope['end']-1]):
        start=scope['body']+m.start();left=scope['body']+m.end()-1
        right=closing(source.code,left,'(',')')
        result.append(dict(name=name,start=start,end=right+1,args=split_args(source.code[left+1:right]),
            evidence=source.cite(start,right+1)))
    return result

def layout(header,field):
    matches=list(re.finditer(rf'\bstruct\s+{re.escape(field["structure"])}\s*\{{(?P<body>[^{{}}]*)\}}\s*__attribute__\s*\(\(\s*packed\s*\)\)\s*;',header.code))
    need(len(matches)==1,'unique packed structure unavailable')
    m=matches[0];members=[];offset=0;payload=None
    for part in re.finditer(r'[^;]+;',m['body']):
        text=part.group().strip();start=m.start('body')+part.start();end=m.start('body')+part.end()
        scalar=re.fullmatch(rf'__(le|be)(16|32|64)\s+({ID})\s*;',text)
        tail=re.fullmatch(rf'char\s+({ID})\s*\[\s*0\s*\]\s*;',text)
        if scalar:
            need(payload is None,'member after zero array unsupported')
            width=int(scalar[2]);size=width//8
            members.append(dict(name=scalar[3],type='__'+scalar[1]+scalar[2],width_bits=width,
                modeled_offset=offset,modeled_size=size,evidence=header.cite(start,end)))
            offset+=size
        elif tail:
            need(payload is None,'multiple trailing arrays unsupported')
            payload=dict(member=tail[1],modeled_offset=offset,element_type='char',declared_count=0,
                evidence=header.cite(start,end))
        else:raise ValueError('unsupported target structure declaration: '+text)
    need(payload is not None,'no trailing char zero array')
    target=[d for d in members if d['name']==field['field']]
    need(len(target)==1 and target[0]['type']==field['type'],'field declaration inconsistent with saved facts')
    return dict(status='source_layout_model',structure=field['structure'],members=members,trailing_array=payload,
        modeled_prefix_bytes=offset,assumptions=['8-bit byte','saved declaration actually binds','packed spelling has expected semantics'],
        actual_layout_certified=False,actual_include_binding_certified=False,full_preprocessing_certified=False,
        evidence=header.cite(m.start(),m.end()))

def macro(source,name,use):
    definitions=list(re.finditer(rf'^\s*#\s*define\s+{re.escape(name)}(?:[ \t]+(?P<value>[^\n]*))?$',source.code,re.M))
    if len(definitions)!=1 or definitions[0].start()>=use or re.search(rf'^\s*#\s*undef\s+{re.escape(name)}\b',source.code,re.M):
        return dict(symbol=name,value=None,status='unresolved',reason='no unique prior direct definition in allowed C',evidence=[])
    d=definitions[0];condition=0
    for directive in re.finditer(r'^\s*#\s*(if|ifdef|ifndef|endif)\b',source.code[:d.start()],re.M):
        condition+=-1 if directive[1]=='endif' else 1
    expression=unwrap(d['value'] or '')
    value=None
    if re.fullmatch(r'0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*',expression):
        value=int(expression,16 if expression.lower().startswith('0x') else (8 if expression.startswith('0') else 10))
    return dict(symbol=name,expression=expression,value=value if condition==0 else None,
        status='direct_nonnegative_literal' if value is not None and condition==0 else 'unresolved',
        reason=None if value is not None and condition==0 else 'nonliteral/conditional macro; no recursive or external resolution',
        evidence=[source.cite(d.start(),d.end())],full_preprocessing_certified=False)

def affine(source,text,use,local_names):
    """Symbolic algebra only; no types, ranges, macro recursion or C semantics."""
    evidence=[];unresolved=[]
    def walk(node):
        if isinstance(node,ast.Constant) and type(node.value) is int and node.value>=0:return node.value,{}
        if isinstance(node,ast.Name):
            if node.id in local_names:return 0,{'local:'+node.id:1}
            fact=macro(source,node.id,use);evidence.append(fact)
            if fact['value'] is not None:return fact['value'],{}
            unresolved.append(node.id);return 0,{'unresolved:'+node.id:1}
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub)):
            c1,t1=walk(node.left);c2,t2=walk(node.right);sign=1 if isinstance(node.op,ast.Add) else -1
            out=dict(t1)
            for key,v in t2.items():out[key]=out.get(key,0)+sign*v
            return c1+sign*c2,{k:v for k,v in out.items() if v}
        raise ValueError('unsupported affine expression')
    constant,terms=walk(ast.parse(text,mode='eval').body)
    return dict(expression=text,constant=constant,symbol_coefficients=terms,
        algebra_domain='unbounded_integers_not_C',nonnegativity_certified=False,
        unresolved_macros=sorted(set(unresolved)),macro_facts=evidence)

def plus(a,b):
    terms=dict(a['symbol_coefficients'])
    for k,v in b['symbol_coefficients'].items():terms[k]=terms.get(k,0)+v
    return dict(constant=a['constant']+b['constant'],symbol_coefficients={k:v for k,v in terms.items() if v})

def inspect(inputs):
    c=Source(inputs['source']);h=Source(inputs['declaration']);facts=inputs['assignment_facts'];field=facts['source_field']
    need(c.meta['revision']==h.meta['revision'],'mixed source revisions')
    result=dict(revision=c.meta['revision'],bounds=inputs['bounds'],layout=None,consumer=None,producer=None,
        complete_length_contract_certified=False,actual_include_binding_certified=False,
        control_flow_certified=False,runtime_execution_certified=False,new_confirmed_cases=0,
        independent_positive_cases=0,project_model_calls=0,partial_failures=[])
    try:result['layout']=layout(h,field)
    except ValueError as e:result['partial_failures'].append(dict(part='layout',reason=str(e)))
    scopes=functions(c)
    consumers=[f for f in scopes if f['name']==inputs['consumer_function']]
    need(len(consumers)==1,'unique selected consumer function unavailable');consumer=consumers[0]
    params=[n for n,p in enumerate(consumer['args']) if re.fullmatch(rf'struct\s+{re.escape(field["structure"])}\s*\*\s*{re.escape(field["object"])}',p)]
    need(len(params)==1,'unique typed object parameter unavailable');param_index=params[0]
    copy_candidates=[call for call in calls(c,consumer,'memcpy') if call['evidence']==inputs['copy_consumer_facts']['evidence']]
    need(len(copy_candidates)==1,'selected copy no longer matches source');copy=copy_candidates[0]
    need(len(copy['args'])==3 and copy['args'][1]==field['object'] and copy['args'][2]==facts['variable'],'copy does not directly use whole object and saved count')
    result['consumer']=dict(function=consumer['name'],operation='memcpy',source_operand=copy['args'][1],
        count_operand=copy['args'][2],copies_from_whole_struct_pointer_syntax=True,object_parameter_index=param_index,
        evidence=copy['evidence'],api_binding_certified=False,pointer_origin_certified=False,copy_validity_certified=False)
    anchor=inputs['producer_anchor_for_scope_only'];anchor_pos=sum(len(t) for t in c.text.splitlines(keepends=True)[:anchor-1])
    producers=[f for f in scopes if f['start']<=anchor_pos<f['end']];need(len(producers)==1,'producer scope anchor ambiguous')
    p=producers[0];handoffs=calls(c,p,consumer['name']);need(len(handoffs)==1,'unique handoff unavailable')
    handoff=handoffs[0];need(len(handoff['args'])>param_index,'missing object argument')
    obj=handoff['args'][param_index];need(re.fullmatch(ID,obj),'handoff object not direct identifier')
    scope=c.code[p['body']:p['end']]
    typed=list(re.finditer(rf'\bstruct\s+{re.escape(field["structure"])}\s+(?P<decl>\*\s*{ID}(?:\s*,\s*\*\s*{ID})*)\s*;',scope))
    need(any(re.search(rf'\*\s*{re.escape(obj)}\b',d['decl']) for d in typed),'caller object declaration missing')
    writes=list(re.finditer(rf'\b{re.escape(obj)}\s*->\s*{re.escape(field["field"])}\s*=\s*(?P<rhs>[^;]+);',scope))
    need(len(writes)==1,'unique encoded field write unavailable');write=writes[0]
    wp=p['body']+write.start();wr=p['body']+write.end();encoding=re.fullmatch(r'htons\s*\((.*)\)',write['rhs'].strip(),re.S)
    need(field['domain']=='be' and field['width']==16 and encoding,'supported BE16 htons writer unavailable')
    need(wr<handoff['start'],'write not lexically before handoff')
    names=set(re.findall(rf'\bint\s+({ID})\s*(?:[;=])',scope))
    length=affine(c,encoding[1].strip(),wp,names)
    prod=dict(function=p['name'],object=obj,encoded_length_expression=encoding[1].strip(),length_affine=length,
        encoding_spelling='htons',encoding_implementation_certified=False,write_evidence=c.cite(wp,wr),
        handoff_evidence=handoff['evidence'],handoff_same_identifier=True,typed_object_scope_evidence=[c.cite(p['body']+d.start(),p['body']+d.end()) for d in typed],
        payload_memcpy_segments=[],typed_payload_stores=[],local_count_writes=[],
        complete_payload_coverage_status='insufficient',complete_payload_coverage_certified=False,
        real_pointer_or_call_binding_certified=False,control_flow_certified=False)
    payload=result['layout']['trailing_array']['member'] if result['layout'] else None
    if payload:
        for call in calls(c,p,'memcpy'):
            if len(call['args'])!=3:continue
            dst=re.fullmatch(rf'{re.escape(obj)}\s*->\s*{re.escape(payload)}(?P<offset>\s*\+.*)?',call['args'][0],re.S)
            if not dst:continue
            offset=(dst['offset'] or '').strip();offset=offset[1:].strip() if offset else '0'
            begin=affine(c,offset,call['start'],names);count=affine(c,call['args'][2],call['start'],names)
            prod['payload_memcpy_segments'].append(dict(offset=begin,count=count,end=plus(begin,count),
                source_operand=call['args'][1],evidence=call['evidence'],api_binding_certified=False,
                conditional_execution_certified=False,count_nonnegative_certified=False))
        for alias in re.finditer(rf'\b(?P<name>{ID})\s*=\s*\(\s*(?P<type>unsigned\s+short)\s*\*\s*\)\s*{re.escape(obj)}\s*->\s*{re.escape(payload)}\s*;',scope):
            stores=list(re.finditer(rf'\*\s*{re.escape(alias["name"])}\s*=\s*(?P<rhs>[^;]+);',scope))
            for store in stores:
                if store.start()<alias.end():continue
                prod['typed_payload_stores'].append(dict(alias=alias['name'],pointed_type=alias['type'],modeled_start_offset=0,
                    width_bytes=None,reason='unsigned short width/actual binding unavailable in allowed sources',
                    alias_evidence=c.cite(p['body']+alias.start(),p['body']+alias.end()),
                    write_evidence=c.cite(p['body']+store.start(),p['body']+store.end()),actual_width_certified=False))
    for name in sorted(names):
        for m in re.finditer(rf'\b{re.escape(name)}\s*=\s*(?P<rhs>[^;]+);',scope):
            prod['local_count_writes'].append(dict(variable=name,rhs=m['rhs'].strip(),
                evidence=c.cite(p['body']+m.start(),p['body']+m.end()),control_flow_value_source_certified=False))
    prod['local_count_unit_links']=[]
    for term in length['symbol_coefficients']:
        if not term.startswith('local:'):continue
        name=term.split(':',1)[1]
        segments=[s for s in prod['payload_memcpy_segments'] if s['count']['constant']==0 and s['count']['symbol_coefficients']=={term:1}]
        writes_for_name=[w for w in prod['local_count_writes'] if w['variable']==name]
        if segments:
            prod['local_count_unit_links'].append(dict(variable=name,also_direct_memcpy_count_syntax=True,
                encoded_sum_term=term,writes=writes_for_name,copy_evidence=[s['evidence'] for s in segments],
                semantic_byte_unit_certified=False,actual_value_source_certified=False))
    unresolved=sorted({symbol for item in [length]+[v[k] for v in prod['payload_memcpy_segments'] for k in ['offset','count']] for symbol in item['unresolved_macros']})
    prod['coverage_blockers']=[
        'nonliteral/external macro numeric evidence missing: '+', '.join(unresolved),
        'typed payload store width not established',
        'conditional local writes, path reachability, nonnegative ranges and object validity not proven',
        'stored total and copied ranges must be related under actual declarations and API semantics',
    ]
    prod['unresolved_macros']=unresolved
    result['producer']=prod
    if result['layout']:
        components=facts['length_components']
        result['prefix_comparison']=dict(modeled_struct_data_offset=result['layout']['modeled_prefix_bytes'],
            observed_addends=[k['value'] for k in components],
            model_matches_single_observed_addend=len(components)==1 and components[0]['value']==result['layout']['modeled_prefix_bytes'],
            actual_layout_or_complete_formula_certified=False,
            note='declaration-model equality; neither macro name nor repair was used as authority')
    statuses={k['name']:dict(status='still_unproved',proven=False,evidence_parts=[],remaining=k['requirement']) for k in inputs['template_facts']['applicability_conditions']}
    if prod['local_count_unit_links']:
        statuses['field_semantic_unit'].update(status='partial_source_support',evidence_parts=['producer.local_count_unit_links'])
    if result.get('prefix_comparison',{}).get('model_matches_single_observed_addend'):
        statuses['explicit_component_meaning'].update(status='partial_source_support',evidence_parts=['layout','consumer','prefix_comparison'])
    if result['layout'] and prod['payload_memcpy_segments']:
        statuses['complete_length_formula'].update(status='partial_source_support',evidence_parts=['producer encoded sum and payload segments; incomplete coverage'])
    result['template_condition_evidence']=statuses
    result['condition_proof_policy']='Partial source support does not certify any original applicability condition.'
    return result
