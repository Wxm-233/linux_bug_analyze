"""Query function extents in the 39 already compiled files touched by misses."""
from collect import *
from concurrent.futures import ProcessPoolExecutor

def query(task):
    entry, targets=task
    os.chdir(entry.directory)
    paths=e.Paths(KSRC,BASE/'riscv_defconfig')
    tu=e.cindex.Index.create().parse(str(entry.source), args=e.parse_args(entry),options=e.DETAIL_RECORD)
    errors=[str(d) for d in tu.diagnostics if d.severity>=e.cindex.Diagnostic.Error]
    assert not errors,errors
    funcs=[]; macros=[]
    def visit(c,p,_):
        if c._kind_id in (e.K.FUNCTION_DECL.value, e.K.MACRO_DEFINITION.value):
            c._tu=tu
            at=paths.location(c,str(entry.directory))
            if at and at[0] in targets:
                if c._kind_id==e.K.MACRO_DEFINITION.value:
                    macros.append({'name':c.spelling,'at':at})
                elif c.is_definition():
                    funcs.append({'name':c.spelling,'at':at,'start':c.extent.start.line,'end':c.extent.end.line,'usr':c.get_usr()})
            if c._kind_id==e.K.FUNCTION_DECL.value: return 1
        return 2
    cb=e.cindex.callbacks['cursor_visit'](visit)
    e.cindex.conf.lib.clang_visitChildren(tu.cursor,cb,None)
    return {'id':entry.number,'source':str(entry.source),'functions':funcs,'macros':macros,'errors':errors}

if __name__=='__main__':
    records=read(HERE/'evidence/compiled_sources.json')
    entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    targets={f for r in read(HERE/'evidence/sample_inputs.json') for f in r['files']}
    with ProcessPoolExecutor(max_workers=4) as pool:
        out=list(pool.map(query,[(entries[int(i)],targets) for i in records]))
    write('evidence/scopes.json',out)
    print('queried',len(out),'units, errors',sum(len(r['errors']) for r in out))
