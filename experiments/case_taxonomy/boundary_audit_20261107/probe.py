from collect import *
import random

units=read(OLD/'units_riscv.json.gz')
inputs=read(OLD/'result_riscv.json')['inputs']
cache=BASE/'enumeration/riscv'/e.digest(inputs)
print('checkpoints', list(cache.glob('*.pickle')))
strata=defaultdict(list)
for u in units:
    f=u['source']
    st='generated' if f.startswith('@build/') else 'arch' if f.startswith('arch/') else 'drivers' if f.startswith('drivers/') else 'public'
    strata[st].append(u)
selection={}
for st,us in sorted(strata.items()):
    us.sort(key=lambda u:hashlib.sha256(f"boundary_audit_20261107:{u['source']}:{u['id']}".encode()).hexdigest())
    selection[st]={'population':len(us),'units':us[:4]}
    for u in us[:4]:
        r=read(cache/f"{u['id']:05d}.json.gz")
        false=Counter(); external=Counter(); candidates=[]
        for at,action,n,owner in r['refs']:
            s=e.Symbol.from_row(r['symbols'][n])
            if not s.defined:
                false[(s.kind,s.external)]+=1
                if s.external: external[(s.kind,s.name,s.at[0])]+=1
                elif len(candidates)<4: candidates.append((s.row(),at))
        print(st,u['id'],u['source'], 'expected',u['unresolved'].get('definition_not_found'), 'false',dict(false),'external top',external.most_common(10),'examples',candidates)
write('evidence/unit_selection.json',selection)
