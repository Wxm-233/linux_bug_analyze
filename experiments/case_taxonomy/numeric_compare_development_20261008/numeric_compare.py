"""Bounded local domain facts, not a C compiler, CFG or runtime verdict."""
from __future__ import annotations
import ast
import importlib.util
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location('fixed_interface_facts', BASE/'interface_facts_20261008/interface_fact_extractor.py')
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
Source = old.Source
ID = r'[A-Za-z_]\w*'
ACCESS = rf'({ID})\s*->\s*({ID})'
CONVERSIONS = [f'{r}{n}_to_cpu' for r in ('le','be') for n in (16,32,64)] + [f'cpu_to_{r}{n}' for r in ('le','be') for n in (16,32,64)]


def unknown(reason):
    return dict(domain='unknown', reason=reason, evidence=[])


def split_top(text, operators):
    """Only operators at parenthesis depth zero; reject malformed nesting."""
    hits, depth, i = [], 0, 0
    while i < len(text):
        if text.startswith('->',i):
            i += 2
            continue
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth < 0: raise ValueError('unbalanced expression')
        elif depth == 0:
            op = next((x for x in operators if text.startswith(x, i)), None)
            if op:
                hits.append((i, op)); i += len(op); continue
        i += 1
    if depth: raise ValueError('unbalanced expression')
    return hits


def logic_atoms(text, start):
    lead = len(text)-len(text.lstrip())
    text, start = text.strip(), start+lead
    while text.startswith('(') and old.closing_delimiter(text,0,'(',')') == len(text)-1:
        text, start = text[1:-1], start+1
        lead = len(text)-len(text.lstrip()); text, start = text.strip(), start+lead
    hits = split_top(text, ('&&','||'))
    if not hits: return [(text,start,start+len(text))]
    answer, cursor = [], 0
    for i, op in hits:
        answer += logic_atoms(text[cursor:i],start+cursor)
        cursor = i+len(op)
    return answer+logic_atoms(text[cursor:],start+cursor)


def unsigned_width(type_name):
    m = re.fullmatch(r'u(8|16|32|64)|__(?:le|be)(16|32|64)',type_name)
    return int(next(x for x in m.groups() if x)) if m else None


def numeric_literal(expr):
    # sizeof of these fixed-width type names is a syntactic constant witness.
    expr = re.sub(r'\bsizeof\s*\(\s*u(8|16|32|64)\s*\)', lambda m:str(int(m.group(1))//8), expr)
    expr = re.sub(r'\b(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]+\b', r'\1', expr)
    if re.search(r'[^0-9a-fA-FxX\s()+*\-<>&|^]',expr): raise ValueError('not a literal arithmetic expression')
    tree = ast.parse(expr.strip(),mode='eval').body
    def calc(n):
        if isinstance(n,ast.Constant) and type(n.value) is int: return n.value
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            return calc(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            a,b=calc(n.left),calc(n.right)
            if abs(a)>2**64 or abs(b)>2**64: raise ValueError('constant outside bounded range')
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,(ast.LShift,ast.RShift)) and 0<=b<64:
                return a<<b if isinstance(n.op,ast.LShift) else a>>b
            if isinstance(n.op,ast.BitOr):return a|b
            if isinstance(n.op,ast.BitAnd):return a&b
            if isinstance(n.op,ast.BitXor):return a^b
        raise ValueError('unsupported constant operator')
    value=calc(tree)
    if not 0<=value<2**64: raise ValueError('negative/overflow constant')
    return value


class Inspector:
    def __init__(self,src,name,declarations):
        self.src=src; self.f=old.function(src,name); self.name=name
        self.declarations=declarations; self.active=set()
        body=src.clean[self.f['body']:self.f['end']]
        self.helper_shadow=any(re.search(rf'\b{h}\b',self.f['params']) or
                               re.search(rf'\(\s*\*\s*{h}\b|(?:^|[;{{}}])\s*(?:const\s+)?{ID}\s+{h}\b',body,re.M)
                               for h in CONVERSIONS)
        self.type_shadow=bool(re.search(r'\btypedef\b[^;]*\bu(?:8|16|32|64)\s*;',body))
        type_names=r'u(?:8|16|32|64)'
        # In C, sizeof(u64) denotes an expression if u64 is a variable name.
        declared_names=self.f['params']+';'+body
        for m in re.finditer(rf'\b({ID})\s+\**\s*({type_names})\b',declared_names):
            if m.group(1) not in ('return','sizeof','case'):
                self.type_shadow=True
        for m in re.finditer(rf'\b(?:{old.SCALAR}|int|long)\s+([^;{{}}]+);',body):
            if re.search(rf'(?:^|,)\s*{type_names}\s*(?:,|=|$)',m.group(1)):
                self.type_shadow=True

    def field(self, obj, member):
        segment=self.src.clean[self.f['start']:self.f['end']]
        matches=list(re.finditer(rf'\bstruct\s+({ID})\s*\*\s*{re.escape(obj)}\b',segment))
        if len(matches)!=1:raise ValueError('structure pointer declaration absent/ambiguous')
        structure=matches[0].group(1)
        binding=old.bind_object(self.src,self.f,obj,structure)
        if old.macro_override(self.src,[obj,member,structure,*CONVERSIONS]):
            raise ValueError('local macro override of field/object/helper')
        found=[]
        for source in self.declarations:
            if source.revision!=self.src.revision:raise ValueError('mixed source revisions')
            try: found.append((source,old.field(source,structure,member)))
            except ValueError: pass
        if len(found)!=1:raise ValueError('direct scalar field declaration absent/ambiguous')
        source, decl=found[0]
        if old.macro_override(source,[member,structure,decl['type'],*CONVERSIONS]):
            raise ValueError('local macro override of declaration/helper')
        width=unsigned_width(decl['type'])
        rep=old.representation(decl['type'])
        if width is None or rep not in ('le','be'):raise ValueError('field has no declared encoded domain')
        # Origin assignment is a fact; its macro/call/offset semantics are not certified.
        origin=[]
        for m in re.finditer(rf'\b{re.escape(obj)}\s*=(?!=)\s*([^;]+);',segment):
            origin.append(self.src.cite(self.f['start']+m.start(),self.f['start']+m.end()))
        if re.search(rf'(?<!&)\&\s*{re.escape(obj)}\b',segment):raise ValueError('object address escape')
        if len(origin)>1:raise ValueError('multiple object assignments unsupported')
        return dict(domain=rep,width=width,type=decl['type'],field=member,object=obj,structure=structure,
                    evidence=[decl['evidence'],binding],object_origin=origin,pointer_origin_certified=False)

    def local(self,name,site):
        if name in self.active: return unknown('recursive local value dependency')
        self.active.add(name)
        try:return self.local_inner(name,site)
        finally:self.active.remove(name)

    def local_inner(self,name,site):
        body=self.src.clean[self.f['body']:self.f['end']]
        full=self.src.clean[self.f['start']:self.f['end']]
        if self.type_shadow or self.helper_shadow or old.macro_override(self.src,[name,*CONVERSIONS,'u8','u16','u32','u64']):return unknown('local scalar/helper/type override')
        if re.search(rf'(?<!&)\&\s*{re.escape(name)}\b',full):return unknown('local scalar address escape')
        # Only known unsigned declarations with plain declarators; typed parameters need caller evidence.
        if re.search(rf'\b(?:{old.SCALAR})\s+{re.escape(name)}\b',self.f['params']):
            return unknown('parameter value origin unknown')
        decls=[]
        for m in re.finditer(rf'\b({old.SCALAR})\s+([^;{{}}]+);',body):
            entries=split_top(m.group(2),(',',))
            cursor=0
            for end,op in entries+[(len(m.group(2)),'')]:
                piece=m.group(2)[cursor:end].strip();cursor=end+len(op)
                if re.search(rf'\b{re.escape(name)}\b',piece):
                    dm=re.fullmatch(rf'{re.escape(name)}(?:\s*=\s*(.+))?',piece,re.S)
                    if not dm:return unknown('array/pointer/complex scalar declaration')
                    decls.append((m.group(1),self.f['body']+m.start(),self.f['body']+m.end(),dm.group(1)))
        if len(decls)!=1:return unknown('local scalar declaration absent/shadowed')
        type_name,begin,end,init=decls[0]
        width=unsigned_width(type_name)
        if width is None or not type_name.startswith('u'):return unknown('only unsigned fixed-width local storage supported')
        # Unknown typedef/signed shadow declarations must not evade known-type lookup.
        for m in re.finditer(rf'\b({ID})\s+\**\s*{re.escape(name)}\s*(?=[;,=\[])',full):
            if m.group(1) not in (type_name,'return'):return unknown('opaque or different-type shadow')
        before=self.src.clean[self.f['body']:site]
        if re.search(r'\b(?:goto|switch|case)\b|\w+\s*:(?!:)',before):return unknown('jump/control context unsupported')
        writes=[]
        for m in re.finditer(rf'(?<![\w>.]){re.escape(name)}\s*(=(?!=)|\+=|-=|\*=|\|=|&=|\^=|<<=|>>=)\s*([^;]*);',body):
            op=m.group(1)
            start=self.f['body']+m.start()
            if start>=site:continue
            writes.append((start,self.f['body']+m.end(),op,m.group(2).strip()))
        if not writes:return unknown('no supported initialization before use')
        first=writes[0]
        prefix=self.src.clean[self.f['body']:first[0]]
        # A direct function-body initialization, no condition/loop prefix or brace scope.
        if prefix.count('{')!=prefix.count('}'):return unknown('initialization in nested block')
        tail=re.split(r'[;{}]',prefix)[-1].strip()
        if init is None and tail:return unknown('conditional/non-direct initialization')
        if init is not None and not re.fullmatch(rf'{type_name}\s+',tail+' '):return unknown('complex declaration initialization')
        if first[2]!='=':return unknown('compound assignment without initial value')
        # Calls mentioning the local can be macros that alter it; only exact domain helpers are admitted.
        for call in re.finditer(rf'\b({ID})\s*\(',full):
            close=old.closing_delimiter(full,call.end()-1,'(',')')
            if close is None:continue
            args=full[call.end():close]
            if re.search(rf'\b{re.escape(name)}\b',args) and call.group(1) not in (*CONVERSIONS,'if','while','for','sizeof'):
                return unknown('unknown call/macro may use or alter local')
        if re.search(rf'(?:\+\+|--)\s*{re.escape(name)}\b|\b{re.escape(name)}\s*(?:\+\+|--)',full):
            return unknown('increment/decrement form unsupported')
        current=None; origins=[]
        for a,z,op,rhs in writes:
            value=self.operand(rhs,a)
            if value['domain']=='unknown':return unknown('unknown local write source: '+value['reason'])
            if value.get('width') is not None and value['width']!=width:return unknown('write storage/source width mismatch')
            if value.get('value') is not None and value['value']>=2**width:return unknown('constant does not fit storage')
            domain='host' if value['domain']=='zero' else value['domain']
            if op!='=' and (current is None or current['domain']!='host' or domain!='host'):
                return unknown('compound arithmetic on encoded/unknown value')
            if current is not None and current['domain']!=domain:return unknown('mixed domains across visible writes')
            current=dict(domain=domain,width=width,type=type_name)
            origins.append(dict(operator=op,rhs=rhs,evidence=self.src.cite(a,z),source=value))
        return dict(**current,evidence=[self.src.cite(begin,end)],visible_writes=origins,
                    value_origin_scope='bounded_local_write_shapes',runtime_value_proven=False,control_flow_certified=False)

    def operand(self,expr,site):
        expr=old.unwrap(expr.strip())
        if re.search(r'[?:,{}\[\]]|(?<![!<>=])=(?!=)',expr):return unknown('complex/assignment operand')
        if self.helper_shadow or old.macro_override(self.src,CONVERSIONS):return unknown('local conversion helper override')
        if re.search(r'\bsizeof\b',expr) and (self.type_shadow or old.macro_override(self.src,['u8','u16','u32','u64'])):
            return unknown('sizeof type macro/typedef override')
        conv=re.fullmatch(r'(le|be)(16|32|64)_to_cpu\s*\((.*)\)',expr,re.S)
        enc=re.fullmatch(r'cpu_to_(le|be)(16|32|64)\s*\((.*)\)',expr,re.S)
        if conv or enc:
            m=conv or enc; inner=self.operand(m.group(3),site); width=int(m.group(2))
            if inner.get('width') is not None and inner['width']!=width:return unknown('conversion width mismatch')
            if conv and inner['domain']!=m.group(1):return unknown('decode source domain mismatch')
            if enc and inner['domain'] not in ('host','zero'):return unknown('encode source domain mismatch')
            if inner.get('value') is not None and inner['value']>=2**width:return unknown('conversion constant outside width')
            return dict(domain='host' if conv else m.group(1),width=width,conversion=m.group(0).split('(')[0].strip(),
                        source=inner,evidence=inner.get('evidence',[]),helper_full_preprocessing_certified=False)
        access=re.fullmatch(ACCESS,expr)
        if access:
            try:return self.field(*access.groups())
            except ValueError as e:return unknown(str(e))
        # If fixed-size scalar sizeof is part of a host constant expression, preserve its origin shape.
        try:
            value=numeric_literal(expr)
            return dict(domain='zero' if value==0 else 'host',value=value,width=None,evidence=[],source_expression=expr,
                        constant_model='fixed-width type names and 8-bit bytes; compiler ABI not verified')
        except (ValueError,SyntaxError):pass
        if re.fullmatch(ID,expr):return self.local(expr,site)
        return unknown('unsupported operand expression')

    def classify(self,atom,site):
        refs=list(re.finditer(ACCESS,atom))
        if not refs:return None
        result=dict(function=self.name,expression=atom,evidence=self.src.cite(site,site+len(atom)),
                    status='insufficient',reason='unsupported atom',normal_scope='local_logical_atom',
                    runtime_value_proven=False,control_flow_certified=False,pointer_origin_certified=False,
                    actual_path='unknown',whole_function_certified=False,full_preprocessing_certified=False)
        if len({m.groups() for m in refs})!=len(refs):
            return dict(result,reason='repeated field in one atom unsupported')
        # Only fixed direct scalar sizeof references, never VLA/array/opaque definitions.
        sizes=list(re.finditer(rf'\bsizeof\s*\(\s*{ACCESS}\s*\)',atom))
        if sizes and len(sizes)==len(refs):
            values=[self.operand(m.group(0)[m.group(0).find('(')+1:-1],site) for m in sizes]
            if all(v['domain']!='unknown' for v in values):
                return dict(result,status='not_value_read',reason='fixed declared scalar sizeof, no field value load',operands=values)
        if re.search(r'[?:,{}]|(?<![!<>=])=(?!=)',atom):return dict(result,reason='ternary/comma/assignment atom')
        compare=split_top(atom,('!=','==','<=','>=','<','>'))
        if compare:
            if len(compare)!=1:return dict(result,reason='multiple/chained comparisons')
            i,op=compare[0]; left=self.operand(atom[:i],site); right=self.operand(atom[i+len(op):],site)
            result.update(use_kind='numeric_comparison',operator=op,left=left,right=right)
            if 'unknown' in (left['domain'],right['domain']):return dict(result,reason='operand domain insufficient')
            if 'zero' in (left['domain'],right['domain']):
                return dict(result,status='normal' if op in ('==','!=') else 'insufficient',
                            reason='endian-invariant zero equality' if op in ('==','!=') else 'ordered zero comparison not certified')
            widths={v['width'] for v in (left,right) if v.get('width') is not None}
            if len(widths)>1:return dict(result,reason='comparison width mismatch')
            width=next(iter(widths),None)
            if width and any(v.get('value',0)>=2**width for v in (left,right)):return dict(result,reason='literal outside field width')
            if left['domain']==right['domain']:
                if left['domain']=='host' or op in ('==','!='):
                    return dict(result,status='normal',reason='matching local comparison domains')
                return dict(result,reason='encoded ordering is not numeric ordering')
            if set((left['domain'],right['domain'])) in ({'host','le'},{'host','be'}):
                return dict(result,status='candidate',reason='host numeric operand compared with undecoded encoded field',
                            candidate_condition='requires byte-order-sensitive value and actual runtime reachability')
            return dict(result,reason='mixed encoded domains unsupported')
        masks=split_top(atom,('&',))
        if len(masks)==1:
            i,_=masks[0];left=self.operand(atom[:i],site);right=self.operand(atom[i+1:],site)
            result.update(use_kind='mask_predicate',left=left,right=right)
            if 'unknown' in (left['domain'],right['domain']):return dict(result,reason='mask operand insufficient')
            if left.get('width') and right.get('width') and left['width']!=right['width']:return dict(result,reason='mask width mismatch')
            if left['domain']==right['domain']:
                return dict(result,status='normal',reason='mask operands in same local representation domain')
            if set((left['domain'],right['domain'])) in ({'host','le'},{'host','be'}):
                return dict(result,status='candidate',reason='raw encoded mask against host operand; mask value/path unproved')
            return dict(result,reason='mask domains unsupported')
        value=self.operand(atom[1:].strip() if atom.startswith('!') else atom,site)
        result.update(use_kind='zero_presence',operand=value)
        if value['domain']!='unknown':return dict(result,status='normal',reason='local zero/presence predicate')
        return result


def inspect_function(src,name,declaration_sources=None):
    declarations=declaration_sources or [src]
    try:
        ins=Inspector(src,name,declarations); out=[]; atom_count=0
        for call in old.calls(src,ins.f['body'],ins.f['end'],'if'):
            if len(call['args'])!=1:continue
            opening=src.clean.find('(',call['begin'],call['end'])
            expression=src.clean[opening+1:call['end']-1]
            for atom,a,z in logic_atoms(expression,opening+1):
                atom_count+=1
                value=ins.classify(atom,a)
                if value is not None:out.append(value)
        return dict(function=name,execution_status='ok',enumerated_logical_atoms=atom_count,field_atoms=out,
                    function_selection='supplied by caller',whole_function_certified=False)
    except (ValueError,SyntaxError) as e:
        return dict(function=name,execution_status='insufficient',reason=str(e),enumerated_logical_atoms=0,field_atoms=[])


def domain_witnesses(src,function_name,structure,member):
    """Syntax sightings; binding success is independent of witnessing a call."""
    try:f=old.function(src,function_name)
    except ValueError as e:return dict(function=function_name,status='insufficient',reason=str(e),sightings=[])
    sightings=[];seen=set()
    try:declared_field=old.field(src,structure,member)
    except ValueError as e:return dict(function=function_name,status='insufficient',reason=str(e),sightings=[])
    for m in re.finditer(rf'\b({ID})\s*->\s*{re.escape(member)}\b',src.clean[f['body']:f['end']]):
        a=f['body']+m.start();z=f['body']+m.end();obj=m.group(1)
        if not re.search(rf'\bstruct\s+{re.escape(structure)}\s*\*\s*{re.escape(obj)}\b',src.clean[f['start']:f['end']]):
            continue
        line_start=src.clean.rfind('\n',0,a)+1;line_end=src.clean.find('\n',z)
        if line_end<0:line_end=len(src.clean)
        text=src.clean[line_start:line_end]
        helper=re.search(r'\b(cpu_to_(?:le|be)(?:16|32|64)|(?:le|be)(?:16|32|64)_to_cpu)\s*\(',text)
        if not helper:continue
        key=(line_start,line_end,helper.group(1))
        if key in seen:continue
        seen.add(key)
        try:binding=old.bind_object(src,f,obj,structure);status='bound_declared_pointer'
        except ValueError as e:binding=dict(reason=str(e));status='insufficient'
        sightings.append(dict(helper_name=helper.group(1),object=obj,structure=structure,field=member,
                              declared_field=declared_field,binding_status=status,binding=binding,
                              evidence=src.cite(line_start,line_end),helper_to_occurrence_dataflow_certified=False,
                              pointer_origin_certified=False,actual_path='unknown'))
    return dict(function=function_name,status='syntax_witness_only',sightings=sightings,
                external_format_authority_certified=False,full_value_flow_certified=False)
