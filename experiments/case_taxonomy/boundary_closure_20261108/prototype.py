"""Per-TU conservative macro dependency and typed callback evidence prototype.

This does not replace Clang's preprocessor or perform a whole-program points-to
analysis. Every unsupported/open binding keeps the containing region pending.
"""
from collections import defaultdict, deque
import gzip
import re
from clang import cindex as ci
from common import *

K=ci.CursorKind
DECLS={K.FUNCTION_DECL:'function',K.VAR_DECL:'object',K.STRUCT_DECL:'struct',
       K.UNION_DECL:'union',K.TYPEDEF_DECL:'typedef',K.ENUM_CONSTANT_DECL:'enum_constant'}
LANGUAGE=set('sizeof typeof __typeof__ __auto_type __extension__ asm __asm__ volatile const '
             'struct union enum void char short int long unsigned signed float double bool '
             '_Bool _Generic __builtin_offsetof do while if else return for switch case break '
             'default static inline __inline__ __volatile__ __alignof__ _Alignof __attribute__'.split())

def walk(cursor):
    yield cursor
    for child in cursor.get_children(): yield from walk(child)

class Unit:
    def __init__(self,source,args,cwd,root,build=None):
        self.source=Path(source).resolve();self.args=args;self.cwd=Path(cwd)
        self.root=Path(root).resolve();self.build=Path(build).resolve() if build else None
        previous=Path.cwd()
        try:
            os.chdir(cwd)
            self.tu=ci.Index.create().parse(str(source),args=args,
                        options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        finally: os.chdir(previous)
        self.errors=[str(d) for d in self.tu.diagnostics if d.severity>=ci.Diagnostic.Error]
        if self.errors: raise RuntimeError(self.errors)

    def path(self,file):
        if not file: return None
        p=Path(file.name if hasattr(file,'name') else file)
        if not p.is_absolute(): p=self.cwd/p
        p=p.resolve()
        if self.build and p.is_relative_to(self.build): return '@build/'+p.relative_to(self.build).as_posix()
        return p.relative_to(self.root).as_posix() if p.is_relative_to(self.root) else None

    def at(self,c):
        return {'file':self.path(c.location.file),'line':c.location.line,'column':c.location.column}

    def region(self,c):
        return {'file':self.path(c.extent.start.file),'start':c.extent.start.line,
                'end':c.extent.end.line,'start_column':c.extent.start.column,'end_column':c.extent.end.column}

    def identity(self,c):
        d=c.get_definition() or c
        at=self.at(d)
        return f"{at['file']}:{at['line']}:{at['column']}:{d.get_usr()}"

    def symbol(self,c):
        d=c.get_definition() or c
        return {'id':self.identity(d),'name':d.spelling,'kind':DECLS.get(d.kind,'unknown'),
                'definition':self.at(d),'usr':d.get_usr(),'defined':d.is_definition(),
                'canonical_type':d.type.get_canonical().spelling}

    def preprocess(self,output):
        argv=['clang',*self.args,'-E','-dD',str(self.source)]
        p=subprocess.run(argv,cwd=self.cwd,capture_output=True,text=True,encoding='utf-8',errors='replace')
        assert p.returncode==0,(argv,p.stderr[-2000:])
        with gzip.open(output,'wt',encoding='utf-8') as f: f.write(p.stdout)
        return {'command':argv,'cwd':str(self.cwd),'exit_code':p.returncode,'stderr':p.stderr,
                'trace_file':str(output),'trace_sha256':sha(output),
                'undef_names':sorted(set(re.findall(r'^#undef\s+([A-Za-z_]\w*)',p.stdout,re.M))),
                'macro_undef_cursor_available':hasattr(K,'MACRO_UNDEFINITION')}

def macro_body(c):
    tokens=[t for t in c.get_tokens() if t.kind!=ci.TokenKind.COMMENT]
    params=set();start=1
    functionlike=(len(tokens)>1 and tokens[1].spelling=='(' and tokens[1].extent.start.offset==tokens[0].extent.end.offset)
    if functionlike:
        depth=0
        for i,t in enumerate(tokens[1:],1):
            if t.spelling=='(':depth+=1
            elif t.spelling==')':
                depth-=1
                if not depth:start=i+1;break
            elif t.kind==ci.TokenKind.IDENTIFIER:params.add(t.spelling)
        if any(t.spelling=='...' for t in tokens[1:start]):params.add('__VA_ARGS__')
    return [t.spelling for t in tokens[start:]],params,functionlike

def macros(unit,trace,root_names=None,root_file=None,compact=False):
    definitions={};by_name=defaultdict(list);inst=[];decl=defaultdict(dict)
    for c in unit.tu.cursor.get_children():
        if c.kind==K.MACRO_DEFINITION and unit.path(c.location.file):
            ident=unit.identity(c)
            body,params,functionlike=macro_body(c)
            definitions[ident]={'id':ident,'name':c.spelling,'definition':unit.at(c),'region':unit.region(c),
                                'tokens':body,'parameters':sorted(params),'functionlike':functionlike}
            if ident not in by_name[c.spelling]:by_name[c.spelling].append(ident)
        elif c.kind==K.MACRO_INSTANTIATION and unit.path(c.location.file):
            inst.append({'name':c.spelling,'use':unit.at(c),'region':unit.region(c),
                         'definition_id':unit.identity(c.referenced) if c.referenced else None})
    for c in walk(unit.tu.cursor):
        if c.kind not in DECLS or not c.spelling or not unit.path(c.location.file):continue
        if c.kind==K.VAR_DECL and c.semantic_parent.kind!=K.TRANSLATION_UNIT:continue
        s=unit.symbol(c)
        decl[c.spelling][s['id']]=s
    undef=set(trace['undef_names'])
    # Source inspection supplements preprocessors that do not preserve #undef.
    files={str(unit.source)}
    for inclusion in unit.tu.get_includes():
        if unit.path(inclusion.include):files.add(inclusion.include.name)
    for file in files:
        fp=Path(file)
        if not fp.is_absolute():fp=unit.cwd/fp
        if fp.is_file():
            undef.update(re.findall(r'^\s*#\s*undef\s+([A-Za-z_]\w*)',fp.read_text(errors='replace'),re.M))
    adjacency={};pending={}
    for ident,r in definitions.items():
        edges=[];unknown=[]
        if r['parameters']:unknown.append('parameter_substitution_requires_expansion_context')
        if '#' in r['tokens'] or '##' in r['tokens']:unknown.append('stringification_or_token_pasting')
        if len(by_name[r['name']])>1:unknown.append('multiple_definition_versions')
        if r['name'] in undef:unknown.append('undef_or_redefinition_requires_expansion_time_binding')
        for n in sorted(set(r['tokens'])):
            if not re.fullmatch(r'[A-Za-z_]\w*',n) or n in set(r['parameters'])|LANGUAGE:continue
            if n in by_name:
                for target in by_name[n]:edges.append({'kind':'macro','target':target,'name':n,'evidence':'replacement_token_candidate'})
                if n in undef or len(by_name[n])>1:unknown.append('uncertain_binding:'+n)
            elif n in decl:
                for s in decl[n].values():edges.append({'kind':s['kind'],'target':s['id'],'name':n,'symbol':s,'evidence':'identifier_definition_candidate'})
            else:
                unknown.append('identifier_requires_substitution_or_type_resolution:'+n)
        adjacency[ident]=edges;pending[ident]=sorted(set(unknown))
    if compact:
        # Batch evidence keeps the graph once and all invocation regions. Precise
        # expansion-time binding is still open, so no invocation is silently closed.
        return {'definition_count':len(definitions),'definitions':definitions,
                'candidate_edges':adjacency,'definition_pending_reasons':pending,
                'outer_regions':[r|{'pending_region':r['region'],
                                   'pending_reasons':['expansion_time_bindings_and_argument_substitution_not_closed']}
                                 for r in inst],
                'preprocessor':trace,'undef_names':sorted(undef),'whole_program_complete':False,
                'scope':'per-TU potential dependency graph plus conservative unresolved outer regions'}
    expansions=[]
    for outer in inst:
        if root_names and outer['name'] not in root_names:continue
        if root_file and outer['use']['file']!=root_file:continue
        root=outer['definition_id']
        seen=set();todo=[root];reachable=[];reasons=[];cycles=[]
        while todo:
            n=todo.pop()
            if n in seen:continue
            seen.add(n)
            if n not in definitions:
                reasons.append('outer_definition_unavailable');continue
            reasons.extend(pending[n])
            for edge in adjacency[n]:
                reachable.append({'from':n,**edge})
                if edge['kind']=='macro':todo.append(edge['target'])
        # Detect cycles independently of DAG merges; multiple paths alone are not cycles.
        color={}
        def visit(n):
            if color.get(n)==1:cycles.append(n);return
            if color.get(n)==2:return
            color[n]=1
            for e in adjacency.get(n,[]):
                if e['kind']=='macro':visit(e['target'])
            color[n]=2
        if root in definitions:visit(root)
        if cycles:reasons.append('recursive_macro_suppression_requires_preprocessor_semantics')
        names=sorted({definitions[n]['name'] for n in seen if n in definitions}|{e['name'] for e in reachable})
        expansions.append(outer|{'dependency_names':names,'candidate_edges':reachable,
            'macro_definitions':[definitions[n] for n in sorted(seen) if n in definitions],
            'pending_reasons':sorted(set(reasons)),
            'pending_region':outer['region'] if reasons else None,
            'claim':'potential definition dependencies, not an exact expansion trace'})
    return {'definition_count':len(definitions),'recorded_instantiations':inst,'expansions':expansions,
            'undef_names':sorted(undef),'preprocessor':trace,
            'whole_program_complete':False,'scope':'one successfully parsed TU; unresolved outer regions retained'}

def function_type(t):
    t=t.get_canonical()
    if t.kind==ci.TypeKind.POINTER:t=t.get_pointee().get_canonical()
    return t if t.kind in (ci.TypeKind.FUNCTIONPROTO,ci.TypeKind.FUNCTIONNOPROTO) else None

def type_name(t):
    t=t.get_canonical()
    if t.kind==ci.TypeKind.POINTER:
        # Ignore top-level pointer qualifiers, preserve pointed-to qualifiers.
        pointee=t.get_pointee().get_canonical()
        return pointee.spelling+' *'
    return re.sub(r'\b(?:const|volatile|restrict)\s*','',t.spelling).strip()

def signature(t):
    f=function_type(t)
    if f is None:return None
    no_proto=f.kind==ci.TypeKind.FUNCTIONNOPROTO
    return {'result':type_name(f.get_result()),
            'arguments':None if no_proto else [type_name(a) for a in f.argument_types()],
            'variadic':None if no_proto else f.is_function_variadic(),'canonical':f.spelling}

def compatible(a,b):
    if a['result']!=b['result']:return False
    if a['arguments'] is None or b['arguments'] is None:return True
    return a['arguments']==b['arguments'] and a['variadic']==b['variadic']

def contains_callback(t,seen=None):
    seen=set() if seen is None else seen
    t=t.get_canonical()
    if signature(t):return True
    if t.spelling in seen:return False
    seen.add(t.spelling)
    if t.kind in (ci.TypeKind.CONSTANTARRAY,ci.TypeKind.INCOMPLETEARRAY):return contains_callback(t.element_type,seen)
    if t.kind==ci.TypeKind.RECORD:return any(contains_callback(f.type,seen) for f in t.get_fields())
    return False

def callback_collect(unit):
    functions={};sites=[];initializers=[];assignments=[];casts=[];slots=[]
    def scan(c,owner=None):
        if c.kind==K.FUNCTION_DECL and c.is_definition():owner=c
        at=unit.at(c)
        if not at['file'] and c.kind!=K.TRANSLATION_UNIT:return
        if c.kind==K.FUNCTION_DECL and c.spelling:
            s=unit.symbol(c);s['signature']=signature(c.type)
            functions[s['id']]=s
        if c.kind in (K.VAR_DECL,K.PARM_DECL,K.FIELD_DECL) and signature(c.type):
            slots.append({'name':c.spelling,'use':at,'signature':signature(c.type),'owner':unit.at(owner) if owner else None})
        if c.kind==K.VAR_DECL and c.semantic_parent.kind==K.TRANSLATION_UNIT and contains_callback(c.type):
            refs=[]
            descendants=list(walk(c))
            for n in descendants:
                if n.kind==K.DECL_REF_EXPR and n.referenced and n.referenced.kind==K.FUNCTION_DECL:
                    refs.append({'target':unit.symbol(n.referenced),'at':unit.at(n)})
            init=any(n.kind==K.INIT_LIST_EXPR for n in descendants)
            if init or refs:
                toks=[t.spelling for t in c.get_tokens()]
                is_designated=any(toks[i]=='.' and i+2<len(toks) and toks[i+2]=='=' for i in range(len(toks)))
                reasons=[]
                if any(n.kind==K.CSTYLE_CAST_EXPR and signature(n.type) for n in descendants):reasons.append('function_pointer_cast')
                initializers.append({'object':c.spelling,'definition':at,'region':unit.region(c),
                    'form':'designated' if is_designated else 'positional','targets':refs,'pending_reasons':reasons,
                    'pending_region':unit.region(c) if reasons else None})
        if c.kind==K.CSTYLE_CAST_EXPR and signature(c.type):
            casts.append({'use':at,'region':unit.region(owner or c),'reason':'function_pointer_cast_can_bypass_signature_filter'})
        if c.kind==K.BINARY_OPERATOR:
            children=list(c.get_children())
            if children and signature(children[0].type) and '=' in [t.spelling for t in c.get_tokens()]:
                assignments.append({'name':children[0].spelling,'use':at,'region':unit.region(owner or c),
                                    'reason':'runtime_assignment_requires_value_flow'})
        if c.kind==K.CALL_EXPR:
            decl=c.referenced
            if decl is None or decl.kind!=K.FUNCTION_DECL:
                children=list(c.get_children())
                sig=signature(children[0].type) if children else None
                sites.append({'name':c.spelling,'use':at,'signature':sig,'region':unit.region(owner or c),
                              'owner':unit.symbol(owner) if owner else None})
        for child in c.get_children():scan(child,owner)
    scan(unit.tu.cursor)
    return {'functions':list(functions.values()),'indirect_sites':sites,'initializers':initializers,
            'runtime_assignments':assignments,'casts':casts,'pointer_slots':slots}

def callback_link(units):
    funcs={s['id']:s for u in units for s in u['functions']}
    result=[]
    for u in units:
        for site in u['indirect_sites']:
            sig=site['signature']
            candidates=[f for f in funcs.values() if f['signature'] and (sig is None or compatible(sig,f['signature']))]
            reasons=['other_TUs_and_runtime_values_not_closed']
            if sig is None:reasons.append('unresolved_function_pointer_type')
            if any(not f['defined'] for f in candidates):reasons.append('external_candidate_without_definition')
            if any(v['runtime_assignments'] for v in units):reasons.append('runtime_function_pointer_assignments')
            if any(v['casts'] for v in units):reasons.append('casts_may_add_incompatible_targets')
            result.append(site|{'type_candidates':candidates,'pending_reasons':reasons,'pending_region':site['region'],
                                'complete_target_set':False})
    return {'functions':list(funcs.values()),'indirect_sites':result,
            'initializers':[x for u in units for x in u['initializers']],
            'runtime_assignments':[x for u in units for x in u['runtime_assignments']],
            'casts':[x for u in units for x in u['casts']],
            'pointer_slots':[x for u in units for x in u['pointer_slots']],
            'whole_program_complete':False,
            'scope':'all canonical-type-compatible functions visible in supplied TUs; static identities preserved; open targets explicitly pending'}
