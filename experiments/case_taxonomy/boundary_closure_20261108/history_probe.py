from common import *

queries={}
for name in ('__pmd_free_tlb','__pud_free_tlb','__p4d_free_tlb','__ro_after_init','__put_user_nocheck'):
    queries[name]={'command':['git','grep','-n','-w',name,'--','arch/riscv/include/asm'],
                   'output':git('grep','-n','-w',name,'--','arch/riscv/include/asm',optional=True)}
write('evidence/history_probe.json',queries)
for n,v in queries.items():
    print(n, v['output'][:1600] if v['output'] else 'absent')

