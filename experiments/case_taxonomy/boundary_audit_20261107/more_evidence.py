from collect import *
queries=[['grep','-n','-E','pgetevent','arch/riscv/include/generated/asm/syscall_table_32.h','arch/riscv/include/generated/asm/syscall_table_64.h'],
 ['llvm-nm','--format=posix','vmlinux']]
out=[]
for q in queries:
    r=run(q,BASE/'riscv_defconfig')
    if q[0]=='llvm-nm':r['stdout']='\n'.join(l for l in r['stdout'].splitlines() if 'pgetevent' in l)
    out.append(r)
queries=[['grep','-n','-E','pgetevent','fs/aio.c','scripts/syscall.tbl','include/uapi/asm-generic/unistd.h'],
 ['grep','-n','-E','__bad_size_call_parameter|wrong_branch_error|lockdep_is_held|__scoped_seqlock_bug|__bad_copy_from','include/linux/percpu-defs.h','include/linux/jump_label.h','include/linux/lockdep.h','include/linux/seqlock.h','include/linux/thread_info.h'],
 ['grep','-n','-E','syscall_table|vdso32-image|capflags|mod.c|filechk_offset','scripts/Makefile.modfinal','scripts/Makefile.modpost','scripts/Makefile.syscalls','arch/riscv/kernel/Makefile','arch/x86/entry/vdso/Makefile','arch/x86/kernel/cpu/Makefile','arch/riscv/include/asm/Kbuild']]
for q in queries:out.append(run(q))
inputs=read(OLD/'result_riscv.json')['inputs'];cache=BASE/'enumeration/riscv'/e.digest(inputs)
entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
for en in entries:
    if en.source==KSRC/'fs/aio.c':
        r=read(cache/f'{en.number:05d}.json.gz')
        out.append({'unit':en.number,'aio_symbols':[s for s in r['symbols'] if 'pgetevent' in s[1]],'aio_defined_ids':r['definitions']})
write('evidence/more_queries.json',out)
print(json.dumps(out[:3],ensure_ascii=False)[:10000])
