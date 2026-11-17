from collect import *

def main():
    refs=read(HERE/'evidence/unresolved_population.json')
    wants=defaultdict(set)
    names=set()
    asm_sources=set()
    for r in refs:
        wants[r['use'][0]].add(r['use'][1]);wants[r['symbol'][3][0]].add(r['symbol'][3][1])
        if r['nm_providers']:
            names.add(r['symbol'][1]);asm_sources.update(p['source'] for p in r['nm_providers'] if p['source'])
    contexts={}
    for name,lines in wants.items():
        fp=BASE/'riscv_defconfig'/name.removeprefix('@build/') if name.startswith('@build/') else KSRC/name
        contexts[name]=context(fp,lines,radius=1)
    write('evidence/unresolved_source_lines.json',contexts)
    q=run(['llvm-nm','--format=posix','vmlinux'],BASE/'riscv_defconfig')
    q['stdout']='\n'.join(l for l in q['stdout'].splitlines() if l.split() and l.split()[0] in names)
    q['output_filter']={'field':0,'names':sorted(names)}
    queries=[q]
    for f in sorted(asm_sources):
        queries.append(run(['grep','-n','-E','SYM_FUNC|SYM_CODE|ENTRY|END|memcpy|memset|clear_page|_start',f]))
    write('evidence/unresolved_asm_definitions.json',queries)
    print('source files',len(contexts),'asm sources',len(asm_sources),'names',len(names))
if __name__=='__main__':main()
