from collect import *
inputs=read(OLD/'result_riscv.json')['inputs'];cache=BASE/'enumeration/riscv'/e.digest(inputs)
entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
out=[]
for en in entries:
    if en.source in [KSRC/'kernel/sys_ni.c',KSRC/'fs/aio.c',KSRC/'arch/riscv/kernel/syscall_table.c',KSRC/'arch/riscv/kernel/compat_syscall_table.c']:
        r=read(cache/f'{en.number:05d}.json.gz'); ss={n:s for n,s in enumerate(r['symbols']) if 'pgetevent' in s[1]}
        out.append({'source':str(en.source),'id':en.number,'symbols':{n:{'row':s,'in_definitions':n in r['definitions']} for n,s in ss.items()},'refs':[ref for ref in r['refs'] if ref[2] in ss]})
write('evidence/aio_debug.json',out)
archive=set(e.command(['llvm-ar','t','vmlinux.a'],BASE/'riscv_defconfig').splitlines())
print('archive aio',[(x,x in archive) for x in ['fs/aio.o','arch/riscv/kernel/syscall_table.o','arch/riscv/kernel/compat_syscall_table.o']])
print('weak', {k:v for k,v in read(OLD/'object_evidence_riscv.json.gz')['weak_overrides'].items() if 'pgetevent' in k})
print(json.dumps(out,ensure_ascii=False))
