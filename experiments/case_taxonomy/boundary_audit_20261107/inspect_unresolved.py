from collect import *
from concurrent.futures import ProcessPoolExecutor

def inspect(task):
    uid, symbols=task
    en=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')[uid]
    paths=e.Paths(KSRC,BASE/'riscv_defconfig');os.chdir(en.directory)
    tu=e.cindex.Index.create().parse(str(en.source),args=e.parse_args(en),options=e.DETAIL_RECORD)
    errors=[str(d) for d in tu.diagnostics if d.severity>=e.cindex.Diagnostic.Error];assert not errors,errors
    keys={(s[0],s[2],tuple(s[3])) for s in symbols};records={};complete={};fnattrs={}
    def visit(c,p,_):
        if c._kind_id in e.DECL_KINDS:
            c._tu=tu;kind=e.DECL_KINDS[c._kind_id];at=paths.location(c,str(en.directory))
            if at:
                usr=c.get_usr();key=(kind,usr,at)
                if kind in ('struct','union') and c.is_definition():complete[usr]={'name':c.spelling,'at':at}
                if key in keys:
                    d=c.get_definition();da=paths.location(d,str(en.directory)) if d else None
                    records[str(key)]={'kind':c.kind.name,'name':c.spelling,'usr':usr,'at':at,'is_definition':c.is_definition(),
                                       'get_definition':da,'linkage':c.linkage.name,'type_size':c.type.get_size(),
                                       'attributes':[x.kind.name for x in c.get_children() if x.kind.is_attribute()] if kind=='function' else []}
        return 2
    cb=e.cindex.callbacks['cursor_visit'](visit);e.cindex.conf.lib.clang_visitChildren(tu.cursor,cb,None)
    return {'id':uid,'declarations':records,'complete_types_by_usr':complete,'errors':errors}

if __name__=='__main__':
    pop=read(HERE/'evidence/unresolved_population.json');tasks=defaultdict(dict)
    for r in pop:tasks[r['unit']][json.dumps(r['symbol'])]=r['symbol']
    with ProcessPoolExecutor(max_workers=4) as pool:out=list(pool.map(inspect,[(uid,list(s.values())) for uid,s in sorted(tasks.items())]))
    write('evidence/unresolved_ast.json',out)
    print('inspected',len(out),'units; declarations',sum(len(r['declarations']) for r in out))
