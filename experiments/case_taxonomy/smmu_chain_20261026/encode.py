"""Selected historical TLBI switch arms only; not queue or hardware execution."""
from pathlib import Path
import json,re,subprocess,hashlib
H=Path(__file__).resolve().parent;S=H/'source'
text=(S/'00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c').read_text();header=(S/'02_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.h').read_text()
start=text.index('\tcase CMDQ_OP_TLBI_NH_VA:');end=text.index('\tcase CMDQ_OP_TLBI_NH_ASID:',start);arms=text[start:end]
assert arms in (S/'01_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c').read_text()
names=sorted(set(re.findall(r'CMDQ_[A-Z0-9_]+',arms))|{'CMDQ_0_OP'})
defs={}
for n in names:
 hit=re.search(r'^\s*#define\s+'+n+r'\s+([^\n]+)',header,re.M);assert hit,n;defs[n]=hit[1]
code=r'''
#include <stdio.h>
#include <stdint.h>
typedef uint64_t u64;
#define GENMASK_ULL(h,l) ((~0ULL << (l)) & (~0ULL >> (63-(h))))
#define FIELD_PREP(m,v) ((((u64)(v)) << __builtin_ctzll(m)) & (m))
#define fallthrough __attribute__((fallthrough))
struct entry {unsigned opcode;struct {unsigned long asid,vmid,addr,ttl,num,scale,tg,leaf;} tlbi;};
'''+ '\n'.join('#define '+n+' '+v for n,v in defs.items())+r'''
static void encode(u64 *cmd,struct entry *ent){cmd[0]=FIELD_PREP(CMDQ_0_OP,ent->opcode);cmd[1]=0;switch(ent->opcode){
'''+arms+r'''
default:break;}}
int main(void){struct entry e;u64 cmd[2];while(scanf("%u %lu %lu %lu %lu %lu %lu %lu %lu",&e.opcode,&e.tlbi.asid,&e.tlbi.vmid,&e.tlbi.addr,&e.tlbi.ttl,&e.tlbi.num,&e.tlbi.scale,&e.tlbi.tg,&e.tlbi.leaf)==9){encode(cmd,&e);printf("%llx %llx\n",(unsigned long long)cmd[0],(unsigned long long)cmd[1]);}return 0;}
'''
p=H/'cmd_build_projection.c';p.write_text(code);exe=H/'cmd_build_projection.bin'
done=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p),'-o',str(exe)],capture_output=True,text=True);assert done.returncode==0,done.stderr
rows=json.loads((H/'chain_results.json').read_text());flat=[(i,j,c) for i,r in enumerate(rows) for j,c in enumerate(r['commands'])]
payload=''.join(' '.join(map(str,c))+'\n' for _,_,c in flat)
out=subprocess.run([str(exe)],input=payload,capture_output=True,text=True,check=True).stdout
lines=out.splitlines();assert len(lines)==len(flat)
def field(word,name):
 match=re.fullmatch(r'GENMASK_ULL\((\d+),\s*(\d+)\)',defs[name].strip());assert match,name
 hi,lo=map(int,match.groups());return (word>>lo)&((1<<(hi-lo+1))-1)
records=[]
for (i,j,c),line in zip(flat,lines):
 w0,w1=(int(x,16) for x in line.split());ttl=field(w1,'CMDQ_TLBI_1_TTL');num=field(w0,'CMDQ_TLBI_0_NUM');scale=field(w0,'CMDQ_TLBI_0_SCALE')
 assert (ttl,num,scale)==tuple(c[k] for k in (4,5,6))
 assert field(w0,'CMDQ_0_OP')==c[0] and field(w1,'CMDQ_TLBI_1_TG')==c[7]
 records.append(dict(case=i,command=j,words=[hex(w0),hex(w1)],ttl=ttl,num=num,scale=scale,range_mode=bool(rows[i]['args'][2]),invalid_range_triple=bool(rows[i]['args'][2]) and ttl==num==scale==0))
result=dict(scope='exact selected switch arms and masks; hand supplied FIELD_PREP and types; not complete build_cmd or queue/device',arm_lines=[text[:start].count('\n')+1,text[:end].count('\n')],source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),records=records)
with (H/'encoding_results.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(encoded_commands=len(records),invalid_range_commands=sum(x['invalid_range_triple'] for x in records))))
