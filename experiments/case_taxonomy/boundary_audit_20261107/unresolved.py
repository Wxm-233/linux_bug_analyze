from collect import *
import random

def main():
    selection=read(HERE/'evidence/unit_selection.json')
    inputs=read(OLD/'result_riscv.json')['inputs'];cache=BASE/'enumeration/riscv'/e.digest(inputs)
    entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    entry_obj={str(x.output.relative_to(BASE/'riscv_defconfig')):x for x in entries}
    paths=e.Paths(KSRC,BASE/'riscv_defconfig')
    selected={u['id']:read(cache/f"{u['id']:05d}.json.gz") for s in selection.values() for u in s['units']}
    needed={s[6] for r in selected.values() for s in r['symbols'] if s[5] and not s[4]}
    nm=run(['llvm-nm','--format=posix','--print-file-name','--extern-only','vmlinux.a'],BASE/'riscv_defconfig')
    providers=defaultdict(list)
    for line in nm['stdout'].splitlines():
        m=re.match(r'vmlinux.a\[(.*?)\]: (\S+) (\S+)',line)
        if m and m[2] in needed and m[3] in e.STRONG_NM|e.WEAK_NM:providers[m[2]].append({'object':m[1],'type':m[3]})
    archive=set(e.command(['llvm-ar','t','vmlinux.a'],BASE/'riscv_defconfig').splitlines())
    definitions=defaultdict(dict);by_object=defaultdict(set)
    target_objs={p['object'] for ps in providers.values() for p in ps}
    # Successful function resolutions include module-only definitions.
    source_units=defaultdict(list)
    for en in entries:source_units[paths.name(str(en.source))].append(en)
    serialized=[]
    with gzip.open(OLD/'direct_calls_riscv.jsonl.gz','rt') as stream:
        for line in stream:
            r=json.loads(line)
            for s in (r['caller'],r['callee']):
                if s['name'] in needed:
                    serialized.append(s)
                    target_objs.update(str(en.output.relative_to(BASE/'riscv_defconfig')) for en in source_units[s['definition']['file']])
    for s in serialized:
        at=s['definition'];symbol=e.Symbol(s['kind'],s['name'],s['usr'],(at['file'],at['line'],at['column']),True,True,s['name'])
        in_core=any(str(en.output.relative_to(BASE/'riscv_defconfig')) in archive for en in source_units[at['file']])
        definitions[(symbol.kind,symbol.usr)][symbol]=in_core or definitions[(symbol.kind,symbol.usr)].get(symbol,False)
    # Module-only objects/functions: use existing module symbol tables, avoiding a whole-tree text query.
    modules=(BASE/'riscv_defconfig/modules.order').read_text().splitlines()
    matched=set()
    for mod,name,code in e.read_nm(modules,BASE/'riscv_defconfig'):
        if name in needed-{'__this_module'} and code in e.STRONG_NM|e.WEAK_NM:matched.add(mod)
    members=set()
    for mod in matched:
        mf=BASE/'riscv_defconfig'/str(Path(mod).with_suffix('.mod'))
        if mf.exists():members.update(mf.read_text().split())
    for obj,name,code in e.read_nm(sorted(members),BASE/'riscv_defconfig'):
        if name in needed and code in e.STRONG_NM|e.WEAK_NM:target_objs.add(obj)
    # Module descriptors live in generated .mod.c. Two are enough to reproduce ambiguity of __this_module.
    for f,ens in source_units.items():
        if f.endswith('.mod.c') and sum(o.endswith('.mod.o') for o in target_objs)<2:
            target_objs.update(str(en.output.relative_to(BASE/'riscv_defconfig')) for en in ens)
    print('target cache objects',len(target_objs),flush=True)
    for idx,obj in enumerate(sorted(target_objs)):
        en=entry_obj.get(obj)
        if not en or not en.is_c:continue
        r=selected.get(en.number) or read(cache/f'{en.number:05d}.json.gz')
        for n in r['definitions']:
            s=e.Symbol.from_row(r['symbols'][n])
            definitions[(s.kind,s.usr)][s]=obj in archive or definitions[(s.kind,s.usr)].get(s,False)
            by_object[(obj,s.kind,s.link_name)].add(s)
        if idx%64==0:print('cache definition queries',idx,flush=True)
    weak=read(OLD/'object_evidence_riscv.json.gz')['weak_overrides']
    write('evidence/definition_lookup.json',{'needed_external_names':len(needed),'candidate_cache_objects':len(target_objs),'providers':providers,'definitions':sum(map(len,definitions.values())),'nm_command':nm['command']})
    allrefs=[];unitstats=[]
    for st,sv in selection.items():
        for u in sv['units']:
            r=selected[u['id']];en=entries[u['id']];obj=str(en.output.relative_to(BASE/'riscv_defconfig')); unresolved=[]
            for at,action,n,owner in r['refs']:
                s=e.Symbol.from_row(r['symbols'][n])
                target,reason=e.resolve(s,obj in archive,definitions,by_object,weak)
                if reason=='definition_not_found':
                    ps=providers.get(s.name,[])
                    actual=[p|{'source':paths.name(str(entry_obj[p['object']].source)) if p['object'] in entry_obj else None} for p in ps]
                    category='forward_type' if s.kind in ('struct','union') else 'builtin' if s.name.startswith('__builtin_') else 'object_or_function_without_C_definition'
                    if actual:
                        layers={e.layer(p['source']) for p in actual if p['source']}
                        category='arch_asm_definition' if layers=={'arch'} else 'public_asm_definition' if layers=={'public'} else 'mixed_providers'
                    unresolved.append({'stratum':st,'unit':u['id'],'use':at,'action':action,'symbol':s.row(),'category':category,'nm_providers':actual})
            expected=u['unresolved'].get('definition_not_found',0)
            unitstats.append({'id':u['id'],'source':u['source'],'stratum':st,'expected':expected,'reproduced':len(unresolved),'matched':expected==len(unresolved)})
            allrefs.extend(unresolved)
            print(u['id'],'expected',expected,'reproduced',len(unresolved),Counter(x['category'] for x in unresolved),flush=True)
    write('evidence/unresolved_population.json',allrefs)
    write('evidence/unresolved_unit_counts.json',unitstats)
    # Save deterministic reference subsample; final classification enriches AST/source evidence separately.
    rng=random.Random(20261107);sample=[]
    for st in sorted(selection):
        group=[r for r in allrefs if r['stratum']==st]
        sample.extend(rng.sample(group,min(100,len(group))))
    write('evidence/unresolved_reference_sample.json',sample)
    print('reconcile',all(u['matched'] for u in unitstats),'count',len(allrefs))
if __name__=='__main__':main()
