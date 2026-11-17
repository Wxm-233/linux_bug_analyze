from collect import *
names=['arch_crash_save_vmcoreinfo','module_alloc','emit_atomic','machine_kexec_mask_interrupts','prepare_elf_headers','reserve_crashkernel_low','reserve_crashkernel_generic','do_misc_fixups','TASK_SIZE_MAX','vmemmap','__put_user_nocheck','riscv_user_regset','copy_sighand','hugetlb_mask_last_page','pudp_huge_get_and_clear','__arch_xchg_masked','SC_RISCV_REGS_TO_ARGS','acpi_processor_ffh_lpi_enter','AT_VECTOR_SIZE_ARCH']
out=[]
for name in names:
    q=run(['git','grep','-n','-w','-e',name,'--','arch/riscv','include','kernel','lib','drivers/acpi','mm'])
    out.append({'name':name,**q})
write('evidence/name_queries.json',out)
config=(BASE/'riscv_defconfig/.config').read_text().splitlines()
confmap={m[1]:line for line in config if (m:=re.match(r'(?:# )?(CONFIG_\w+)(?:=| is not set)',line))}
rows=read(HERE/'evidence/sample_inputs.json')
entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json');paths=e.Paths(KSRC,BASE/'riscv_defconfig')
comp=defaultdict(list)
for en in entries: comp[paths.name(str(en.source))].append({'id':en.number,'source':str(en.source),'object':str(en.output),'command':list(en.args)})
extra=[]
for row in rows:
    files=[]
    for f in row['files']:
        fp=KSRC/f
        lines=fp.read_text(errors='replace').splitlines() if fp.exists() else []
        controls=[{'file':f,'line':i,'text':t} for i,t in enumerate(lines,1) if re.match(r'^\s*#\s*(if|elif|else|endif)',t)]
        cfgs=set(re.findall(r'CONFIG_\w+','\n'.join(t['text'] for t in controls)+json.dumps(next(v['build_rules'] for v in row['current'] if v['file']==f))))
        files.append({'file':f,'compile_entries':comp.get(f,[]),'preprocessor_controls':controls,
                      'config_values':{c:confmap.get(c,'not present in .config') for c in sorted(cfgs)},
                      'full_source_evidence':f'evidence/current/{f}'})
        dest=HERE/'evidence/current'/f;dest.parent.mkdir(parents=True,exist_ok=True)
        if fp.exists():dest.write_text('\n'.join(f'{i}: {l}' for i,l in enumerate(lines,1))+'\n')
    anc=run(['git','merge-base','--is-ancestor',row['commit'],'HEAD'])
    extra.append({'id':row['id'],'fix_is_ancestor':anc['exit_code']==0,'ancestor_command':anc,'files':files})
write('evidence/sample_extra.json',extra)
print('queries',len(out),'extra samples',len(extra))
