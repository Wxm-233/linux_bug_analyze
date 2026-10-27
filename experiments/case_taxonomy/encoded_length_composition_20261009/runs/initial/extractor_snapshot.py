"""Finite syntax witnesses and conditional layout/composition models, not C proof."""
from dataclasses import dataclass
from copy import deepcopy
import hashlib,re

ID=r'[A-Za-z_]\w*'
def need(ok,why):
    if not ok:raise ValueError(why)
def mask(text):
    pattern=r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern,lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),text,flags=re.S)
def close(text,start,left='(',right=')'):
    need(text[start]==left,'opening delimiter missing');depth=0
    for i in range(start,len(text)):
        if text[i]==left:depth+=1
        if text[i]==right:
            depth-=1
            if depth==0:return i
    raise ValueError('unbalanced delimiter')
def unwrap(text):
    text=text.strip()
    while text.startswith('(') and close(text,0)==len(text)-1:text=text[1:-1].strip()
    return text
def split(text,delimiter):
    depth=0;out=[];start=0
    for i,c in enumerate(text):
        if c in '([':depth+=1
        elif c in ')]':depth-=1
        elif c==delimiter and depth==0:out.append(text[start:i].strip());start=i+1
    need(depth==0,'unbalanced expression');out.append(text[start:].strip());return out
def one(items,why):
    need(len(items)==1,why+f' (observed {len(items)})');return items[0]

@dataclass
class Source:
    raw:bytes
    meta:dict
    def __post_init__(self):
        self.text=self.raw.decode('utf-8');self.code=mask(self.text)
        need(hashlib.sha256(self.raw).hexdigest()==self.meta['sha256'],'source SHA mismatch')
        need(hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest()==self.meta['blob_sha1'],'source blob mismatch')
    def quote(self,start,end):
        a=self.text.count('\n',0,start)+1;b=self.text.count('\n',0,max(start,end-1))+1
        return {**{k:self.meta[k] for k in ['revision','source_path','saved_path','sha256','blob_sha1']},
            'start_line':a,'end_line':b,'text':'\n'.join(self.text.splitlines()[a-1:b])}

def function(src,name):
    found=[]
    for m in re.finditer(r'\b'+re.escape(name)+r'\s*\(',src.code):
        opening=src.code.index('(',m.start());end=close(src.code,opening)
        pos=end+1
        while pos<len(src.code) and src.code[pos].isspace():pos+=1
        if pos<len(src.code) and src.code[pos]=='{':
            last=close(src.code,pos,'{','}')
            found.append(dict(start=m.start(),params=src.code[opening+1:end],body_start=pos+1,body_end=last,
                evidence=src.quote(m.start(),last+1)))
    return one(found,'function definition must be unique')

def calls(src,f,name):
    out=[]
    for m in re.finditer(r'\b'+re.escape(name)+r'\s*\(',src.code[f['body_start']:f['body_end']]):
        start=f['body_start']+m.start();opening=src.code.index('(',start);end=close(src.code,opening)
        out.append(dict(start=start,end=end+1,args=split(src.code[opening+1:end],','),evidence=src.quote(start,end+1)))
    return out

def struct_layout(src,name):
    m=one(list(re.finditer(r'\bstruct\s+'+re.escape(name)+r'\s*\{',src.code)),'structure must be unique')
    opening=src.code.index('{',m.start());end=close(src.code,opening,'{','}')
    semicolon=src.code.find(';',end);need(semicolon!=-1,'structure terminator missing')
    attr=re.sub(r'\s+','',src.code[end+1:semicolon])
    need(attr=='__attribute__((packed))','only explicit packed spelling supported')
    body=src.code[opening+1:end];fields=[];position=opening+1
    for piece in body.split(';'):
        if not piece.strip():position+=len(piece)+1;continue
        item=re.fullmatch(r'\s*(?:(__([bl]e)(16|32|64))\s+('+ID+r')|char\s+('+ID+r')\s*\[\s*0\s*\])\s*',piece)
        need(item is not None,'unsupported structure member')
        fields.append(dict(name=item.group(4) or item.group(5),type=item.group(1) or 'char[0]',
            encoded_domain=item.group(2),annotated_width_bits=int(item.group(3)) if item.group(3) else None,
            tail_zero_array=bool(item.group(5)),evidence=src.quote(position,position+len(piece))))
        position+=len(piece)+1
    need(len(fields)>=2 and fields[-1]['tail_zero_array'] and not any(f['tail_zero_array'] for f in fields[:-1]),'one terminal zero-byte array required')
    bits=sum(f['annotated_width_bits'] for f in fields[:-1]);need(bits%8==0,'non-octet scalar layout unsupported')
    return dict(structure=name,fields=fields,packed_spelling=True,structure_evidence=src.quote(m.start(),semicolon+1),
        conditional_prefix_model=bits//8,model_unit='octets_under_assumptions',actual_offset_certified=False,
        assumptions=[dict(name=k,proven=False) for k in ['annotated_type_actual_storage_width','CHAR_BIT_is_8','packed_and_zero_array_actual_layout','actual_include_binding']])

class Algebra:
    """Only addition/literals/object macros; unresolved identifiers stay symbolic."""
    def __init__(self,src):
        self.src=src;self.macros={};self.conditional_macros=set()
        depth=0
        for line in src.code.splitlines():
            if re.match(r'^\s*#\s*if(?:n?def)?\b',line):depth+=1
            elif re.match(r'^\s*#\s*endif\b',line):depth-=1
            definition=re.match(r'^\s*#\s*define\s+('+ID+r')\b',line)
            if definition and depth>0:self.conditional_macros.add(definition.group(1))
        for m in re.finditer(r'^\s*#\s*define\s+('+ID+r')(?=[ \t])[^\S\n]+([^\n]+)',src.code,re.M):
            self.macros.setdefault(m.group(1),[]).append((m.group(2).strip(),src.quote(m.start(),m.end())))
        self.used={}
    def poly(self,expression,seen=()):
        text=unwrap(expression);parts=split(text,'+')
        if len(parts)>1:
            out={'constant':0,'symbols':{}}
            for p in parts:out=self.add(out,self.poly(p,seen))
            return out
        if re.fullmatch(r'0[xX][0-9a-fA-F]+|[0-9]+',text):
            # Reject octal ambiguity instead of interpreting a C literal as decimal.
            need(not (len(text)>1 and text[0]=='0' and text[1] not in 'xX'),'octal literal unsupported')
            return {'constant':int(text,16 if text.lower().startswith('0x') else 10),'symbols':{}}
        need(re.fullmatch(ID,text),'unsupported symbolic expression')
        if text in self.macros:
            expr,q=one(self.macros[text],'ambiguous macro '+text)
            need(text not in self.conditional_macros,'conditional component macro unsupported')
            need(text not in seen and len(seen)<8,'cyclic/deep macro')
            self.used[text]=dict(expression=expr,evidence=q)
            return self.poly(expr,seen+(text,))
        return {'constant':0,'symbols':{text:1}}
    @staticmethod
    def add(a,b):
        symbols=dict(a['symbols'])
        for key,value in b['symbols'].items():symbols[key]=symbols.get(key,0)+value
        return {'constant':a['constant']+b['constant'],'symbols':dict(sorted(symbols.items()))}

def analyze(c,h,selection,template):
    """Selection contains structure/function names, never target lines or fix labels."""
    need(c.meta['revision']==h.meta['revision'],'mixed source versions')
    layout=struct_layout(h,selection['structure']);tail=layout['fields'][-1]['name']
    pf=function(c,selection['producer_function']);cf=function(c,selection['consumer_function'])
    formals=split(cf['params'],',');formal_matches=[]
    for n,param in enumerate(formals):
        m=re.fullmatch(r'\s*struct\s+'+re.escape(selection['structure'])+r'\s*\*\s*('+ID+r')\s*',param)
        if m:formal_matches.append((n,m.group(1)))
    arg_index,consumer_obj=one(formal_matches,'consumer structure-pointer formal must be unique')
    handoff=one(calls(c,pf,selection['consumer_function']),'producer handoff must be unique')
    need(len(handoff['args'])==len(formals),'handoff argument count mismatch')
    obj=handoff['args'][arg_index];need(re.fullmatch(ID,obj),'direct producer object required')
    pointer_writes=list(re.finditer(r'\b'+re.escape(obj)+r'\s*(?:=(?!=)|\+=|-=|\+\+|--)',c.code[pf['body_start']:pf['body_end']]))
    need(len(pointer_writes)==1,'extra producer-object writes unsupported')
    consumer_copy=one([x for x in calls(c,cf,'memcpy') if len(x['args'])==3 and x['args'][1]==consumer_obj],
        'copy from selected object start must be unique')
    count=consumer_copy['args'][2];need(re.fullmatch(ID,count),'direct consumer count required')
    prior=template['observed_assignment'];field=prior['field']['field']
    need(prior['variable']==count and prior['field']['object']==consumer_obj,'prior consumer fact conflict')
    declaration=one([f for f in layout['fields'] if f['name']==field],'length field absent/ambiguous')
    need(declaration['type']=='__be16','only network16 encoded producer supported')
    binding=one(list(re.finditer(r'\b'+re.escape(obj)+r'\s*=\s*\(\s*struct\s+'+re.escape(selection['structure'])+r'\s*\*\s*\)\s*('+ID+r')\s*;',c.code[pf['body_start']:pf['body_end']])),'unique direct buffer binding required')
    buffer=binding.group(1)
    binding_quote=c.quote(pf['body_start']+binding.start(),pf['body_start']+binding.end())
    buffer_decl=one(list(re.finditer(r'\bunsigned\s+char\s+'+re.escape(buffer)+r'\s*\[\s*([0-9]+)\s*\]\s*;',c.code[pf['body_start']:pf['body_end']])),'unique byte buffer declaration required')
    decl_quote=c.quote(pf['body_start']+buffer_decl.start(),pf['body_start']+buffer_decl.end())
    declaration_matches=list(re.finditer(r'\bstruct\s+'+re.escape(selection['structure'])+r'\s+(\*\s*'+ID+r'(?:\s*,\s*\*\s*'+ID+r')*)\s*;',c.code[pf['body_start']:pf['body_end']]))
    names=[name for m in declaration_matches for name in re.findall(r'\*\s*('+ID+r')',m.group(1))]
    need(names.count(obj)==1,'producer object declaration absent/ambiguous')
    writes=list(re.finditer(r'\b'+re.escape(obj)+r'\s*->\s*'+re.escape(field)+r'\s*=(?!=)\s*htons\s*\(',c.code[pf['body_start']:pf['body_end']]))
    all_field_writes=list(re.finditer(r'\b'+re.escape(obj)+r'\s*->\s*'+re.escape(field)+r'\s*(?:=(?!=)|\+=|-=|\+\+|--)',c.code[pf['body_start']:pf['body_end']]))
    need(len(all_field_writes)==1,'extra encoded-field writes unsupported')
    wm=one(writes,'one direct encoded-length write required');ws=pf['body_start']+wm.start();opening=c.code.index('(',pf['body_start']+wm.end()-1);we=close(c.code,opening)
    need(c.code[we+1:we+3].strip()==';','encoded length assignment terminator missing')
    length_expression=c.code[opening+1:we];algebra=Algebra(c);payload=algebra.poly(length_expression)
    copies=[]
    for call in calls(c,pf,'memcpy'):
        if len(call['args'])!=3:continue
        dest=re.sub(r'\s+','',unwrap(call['args'][0]))
        m=re.fullmatch(re.escape(obj)+'->'+re.escape(tail)+r'(?:\+(.+))?',dest)
        if not m:continue
        begin=algebra.poly(m.group(1) or '0');length=algebra.poly(call['args'][2])
        copies.append(dict(destination=call['args'][0],source=call['args'][1],length_expression=call['args'][2],
            begin_model=begin,length_model=length,end_model=algebra.add(begin,length),
            api_unit_assumption='memcpy count in C bytes; actual binding unproved',evidence=call['evidence']))
    need(len(copies)==2,'only one two-copy payload construction supported')
    adjacency=[(i,j) for i,a in enumerate(copies) for j,b in enumerate(copies) if i!=j and a['end_model']==b['begin_model']]
    ai,bi=one(adjacency,'unique symbolic copy adjacency required')
    need(copies[bi]['end_model']==payload,'copy terminal expression differs from encoded payload formula')
    prefix=copies[ai]['begin_model'];need(not prefix['symbols'],'copy prefix must be an observed constant')
    magic_bind=one(list(re.finditer(r'\b('+ID+r')\s*=\s*\(\s*unsigned\s+short\s*\*\s*\)\s*'+re.escape(obj)+r'\s*->\s*'+re.escape(tail)+r'\s*;',c.code[pf['body_start']:pf['body_end']])),'unique scalar pointer binding required')
    magic=magic_bind.group(1)
    scalar_write=one(list(re.finditer(r'\*\s*'+re.escape(magic)+r'\s*=(?!=)\s*htons\s*\([^;]*\)\s*;',c.code[pf['body_start']:pf['body_end']])),'unique scalar store required')
    indirect_writes=list(re.finditer(r'\*\s*'+re.escape(magic)+r'\s*(?:=(?!=)|\+=|-=|\+\+|--)',c.code[pf['body_start']:pf['body_end']]))
    need(len(indirect_writes)==1,'extra indirect scalar writes unsupported')
    scalar_pointer_writes=[]
    body=c.code[pf['body_start']:pf['body_end']]
    for m in re.finditer(r'\b'+re.escape(magic)+r'\s*(?:=(?!=)|\+=|-=|\+\+|--)',body):
        if not body[:m.start()].rstrip().endswith('*'):scalar_pointer_writes.append(m)
    need(len(scalar_pointer_writes)==1,'extra scalar-pointer writes unsupported')
    need(not re.search(r'&\s*(?:'+re.escape(obj)+'|'+re.escape(magic)+r')\b',body),'selected pointer/field address escape unsupported')
    scalar_decl=one(list(re.finditer(r'\bunsigned\s+short\s*\*\s*'+re.escape(magic)+r'\s*;',body)),'unique scalar pointer declaration required')
    old_vars=[s for s in payload['symbols'] if re.search(r'\bint\s+'+re.escape(s)+r'\s*=\s*0\s*;',c.code[pf['body_start']:pf['body_end']])]
    old=one(old_vars,'unique zero-initialized old-count local required')
    old_read=one(list(re.finditer(r'\b'+re.escape(old)+r'\s*=(?!=)\s*ntohs\s*\(\s*('+ID+r')\s*->\s*'+re.escape(field)+r'\s*\)\s*;',c.code[pf['body_start']:pf['body_end']])),'one old-count decode witness required')
    old_obj=old_read.group(1);need(names.count(old_obj)==1,'old-object structure declaration missing')
    old_block=one(list(re.finditer(r'\bif\s*\(\s*'+re.escape(old_obj)+r'\s*\)\s*\{',c.code[pf['body_start']:pf['body_end']])),'one old-object conditional block required')
    ob_start=pf['body_start']+old_block.start();ob_open=c.code.index('{',ob_start);ob_end=close(c.code,ob_open,'{','}')
    guards=[]
    for call in calls(c,pf,'if'):
        if len(call['args'])!=1:continue
        cond=call['args'][0];pieces=split(cond,'>')
        if len(pieces)!=2 or re.sub(r'\s+','',pieces[1])!=f'sizeof({buffer})':continue
        try:poly=algebra.poly(pieces[0])
        except ValueError:continue
        guards.append(dict(expression=cond,count_model=poly,buffer=buffer,
            inside_old_object_block=ob_open<call['start']<ob_end,
            all_paths_certified=False,evidence=call['evidence']))
    guard=one(guards,'one capacity guard syntax witness required')
    header={'constant':layout['conditional_prefix_model'],'symbols':{}}
    total=algebra.add(header,payload)
    observed=one(prior['explicit_components'],'one saved consumer addend required')
    need(observed['value']==header['constant'],'conditional layout prefix differs from observed addend')
    need(guard['count_model']==total and guard['inside_old_object_block'],'capacity witness not matching model/old block')
    for name,witness in algebra.used.items():
        need(witness['evidence']['end_line']<c.quote(ws,we+2)['start_line'],'macro definition after selected use unsupported')
        need(not re.search(r'^\s*#\s*undef\s+'+re.escape(name)+r'\b',c.code,re.M),'undefined component macro unsupported')
    guarded_names={obj,consumer_obj,field,tail,count,magic,'htons','ntohs','memcpy','unsigned','short','char','int','__be16',selection['structure']}
    need(not guarded_names.intersection(algebra.macros),'visible macro shadows selected binding/helper')
    for name in guarded_names:
        need(not re.search(r'^\s*#\s*(?:define|undef)\s+'+re.escape(name)+r'\b',c.code,re.M),'visible selected macro define/undef unsupported')
    conditions=deepcopy(template['applicability_conditions'])
    for condition in conditions:
        condition['proven']=False
        condition['evidence_level']='unresolved'
        if condition['name'] in ['field_semantic_unit','explicit_component_meaning','complete_length_formula']:
            condition['evidence_level']='source_supported_under_assumptions_not_certified'
        condition['reason']='Current syntax/composition witnesses do not certify this runtime/contract condition.'
    return dict(status='source_evidence_collected',source_revision=c.meta['revision'],interface_cases=1,
        machine_facts=dict(layout=layout,producer=dict(function=selection['producer_function'],object=obj,
            buffer=dict(name=buffer,declared_C_bytes=int(buffer_decl.group(1)),evidence=decl_quote,binding_evidence=binding_quote),
            handoff=handoff,encoded_length_write=dict(rhs=length_expression,helper='htons',field=field,
                payload_model=payload,evidence=c.quote(ws,we+2),conversion_binding_certified=False),
            tail_array_copies=copies,symbolic_adjacency=[ai,bi],
            scalar_store=dict(pointer=magic,nominal_type='unsigned short',width_C_bytes='sizeof(unsigned short)',
                covers_prefix_model_only_if_size_matches=prefix['constant'],width_and_alignment_certified=False,
                declaration_evidence=c.quote(pf['body_start']+scalar_decl.start(),pf['body_start']+scalar_decl.end()),
                binding_evidence=c.quote(pf['body_start']+magic_bind.start(),pf['body_start']+magic_bind.end()),
                evidence=c.quote(pf['body_start']+scalar_write.start(),pf['body_start']+scalar_write.end())),
            old_count_read=dict(local=old,old_object=old_obj,evidence=c.quote(pf['body_start']+old_read.start(),pf['body_start']+old_read.end()),
                control_flow_certified=False),capacity_guard=guard),
            consumer=dict(function=selection['consumer_function'],parameter_object=consumer_obj,count_local=count,
                object_start_copy=consumer_copy,observed_addend=deepcopy(observed))),
        conditional_composition=dict(payload_model=payload,prefix_model=header,total_object_model=total,
            copied_intervals_adjacent=True,copy_end_equals_encoded_length_expression=True,
            header_model_equals_visible_addend=True,scalar_prefix_coverage_certified=False,
            actual_layout_certified=False,field_unit_certified=False,whole_payload_coverage_certified=False,
            complete_length_contract_certified=False,all_producer_paths_capacity_checked_certified=False,
            unknown_symbols=sorted(payload['symbols']),unknown_symbols_not_assigned_common_values=True,
            derivation_scope='symbolic syntax and conditional layout; no C execution or full semantic proof'),
        resolved_macro_witnesses=algebra.used,condition_evidence_card=conditions,
        human_contract_layer='Independent saved-source review may support a conditional payload-plus-prefix interpretation; no expert/ABI certification.',
        limits={**deepcopy(template['limits']),'whole_producer_flow_certified':False,'actual_conversion_binding_certified':False,
            'all_paths_buffer_bound_certified':False,'actual_layout_certified':False,'independent_generalization_certified':False},
        new_confirmed_cases=0,independent_positive_cases=0)
