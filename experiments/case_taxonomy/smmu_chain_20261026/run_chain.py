"""Execute original callback/wrappers/range bodies with explicit boundary doubles."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib,re
H=Path(__file__).resolve().parent;S=H/'source'
spec=importlib.util.spec_from_file_location('probe',H.parent/'smmu_range_probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
header=(S/'02_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.h').read_text()
scaffold=m.SCAFFOLD.replace('#include <stdlib.h>','#include <stdlib.h>\n#include <limits.h>')
scaffold=scaffold.replace('struct arm_smmu_domain {','struct arm_smmu_domain {\n int stage; struct {struct {int asid;} cd;} s1_cfg; struct {int vmid;} s2_cfg;')
scaffold=scaffold.replace('struct arm_smmu_cmdq_ent {','struct arm_smmu_cmdq_ent {\n unsigned int opcode;')
scaffold=scaffold.replace('bool leaf;','bool leaf; int asid,vmid;')
scaffold=scaffold.replace('#define ARM_SMMU_FEAT_RANGE_INV 1U','')
macros=[]
for name in ['ARM_SMMU_FEAT_RANGE_INV','ARM_SMMU_FEAT_BTM','ARM_SMMU_FEAT_E2H','CMDQ_OP_TLBI_EL2_VA','CMDQ_OP_TLBI_NH_VA','CMDQ_OP_TLBI_S2_IPA']:
 hit=re.search(r'^\s*#define\s+'+name+r'\s+([^\n]+)',header,re.M);assert hit,name
 macros.append('#define '+name+' '+hit[1])
scaffold+='\n'+'\n'.join(macros)+r'''
#define ARM_SMMU_DOMAIN_S1 1
#define ARM_SMMU_DOMAIN_S2 2
#define IOMMU_NO_PASID 0
#define PAGE_SIZE (1UL << PAGE_SHIFT)
struct mmu_notifier {int unused;};
struct mm_struct {int pasid;};
struct cd {int asid;};
struct arm_smmu_mmu_notifier {struct mmu_notifier mn; struct arm_smmu_domain *domain; struct cd *cd;};
static struct arm_smmu_mmu_notifier *mn_to_smmu(struct mmu_notifier *mn) {return (void *)mn;}
static int asid_calls,asid_value,atc_calls,atc_pasid; static unsigned long atc_start,atc_size;
static void arm_smmu_tlb_inv_asid(struct arm_smmu_device *s,int a){(void)s;asid_calls++;asid_value=a;}
static int arm_smmu_atc_inv_domain(struct arm_smmu_domain *d,int p,unsigned long a,size_t n){(void)d;atc_calls++;atc_pasid=p;atc_start=a;atc_size=n;return 0;}
'''
sva=(S/'03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c').read_text()
callback=m.function(sva,'static void arm_smmu_mm_arch_invalidate_secondary_tlbs(')
main=r'''
int main(int argc,char **argv){
 if(argc!=7)return 2;
 unsigned long mode=strtoul(argv[1],0,0),pages=strtoul(argv[2],0,0),range=strtoul(argv[3],0,0),btm=strtoul(argv[4],0,0),e2h=strtoul(argv[5],0,0),stage=strtoul(argv[6],0,0);
 struct arm_smmu_device smmu={.features=(range?ARM_SMMU_FEAT_RANGE_INV:0)|(btm?ARM_SMMU_FEAT_BTM:0)|(e2h?ARM_SMMU_FEAT_E2H:0)};
 struct arm_smmu_domain d={.smmu=&smmu,.domain={.pgsize_bitmap=PAGE_SIZE|(PAGE_SIZE<<(PAGE_SHIFT-3))},.stage=stage,.s1_cfg={.cd={.asid=23}},.s2_cfg={.vmid=31}};
 struct cd cd={.asid=17};struct mm_struct mm={.pasid=19};struct arm_smmu_mmu_notifier mn={.domain=&d,.cd=&cd};
 unsigned long start=1UL<<30,size=pages*PAGE_SIZE;
 if(mode==2){start=0;size=ULONG_MAX;}
 if(mode==1)arm_smmu_tlb_inv_walk(start,size,PAGE_SIZE,&d);
 else arm_smmu_mm_arch_invalidate_secondary_tlbs(&mn.mn,&mm,start,start+size);
 printf("META %u %d %d %d %d %lu %lu\n",recorded_count,asid_calls,asid_value,atc_calls,atc_pasid,atc_start,atc_size);
 for(unsigned int i=0;i<recorded_count;i++){struct arm_smmu_cmdq_ent *c=&recorded[i];printf("CMD %u %d %d %lu %lu %lu %lu %lu %u\n",c->opcode,c->tlbi.asid,c->tlbi.vmid,c->tlbi.addr,c->tlbi.ttl,c->tlbi.num,c->tlbi.scale,c->tlbi.tg,c->tlbi.leaf);}
 return 0;
}
'''
cases=[];builds=[];bodies=[]
for version,prefix in [('old','00'),('fixed','01')]:
 text=next(S.glob(prefix+'_*')).read_text()
 funcs=[m.function(text,sig) for sig in ['static void __arm_smmu_tlb_inv_range(','static void arm_smmu_tlb_inv_range_domain(','void arm_smmu_tlb_inv_range_asid(','static void arm_smmu_tlb_inv_walk(']]
 bodies.append(dict(version=version,functions=[dict(signature=f.split('{')[0],sha256=hashlib.sha256(f.encode()).hexdigest()) for f in funcs],callback_sha256=hashlib.sha256(callback.encode()).hexdigest()))
 for shift in [12,14,16]:
  p=H/f'{version}_{shift}.c';p.write_text(scaffold+'\n'+'\n'.join(funcs)+'\n'+callback+'\n'+main)
  exe=H/f'{version}_{shift}.bin';argv=['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DPAGE_SHIFT={shift}',str(p),'-o',str(exe)]
  done=subprocess.run(argv,capture_output=True,text=True);assert done.returncode==0,done.stderr
  builds.append(dict(source=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary=exe.name,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),flags=argv[1:-3]))
  inputs=[]
  for pages in [1,33,65]:
   for ril,btm,e2h in [(0,0,0),(1,0,0),(1,1,0),(1,0,1)]:inputs.append(('sva_range',[0,pages,ril,btm,e2h,1]))
  for mode in [0,2]:
   for btm in [0,1]:inputs.append(('sva_zero_or_full',[mode,0,1,btm,0,1]))
  for stage in [1,2]:
   for e2h in [0,1]:inputs.append(('walk_table_shape',[1,1<<(shift-3),1,0,e2h,stage]))
  for kind,args in inputs:
   run=subprocess.run([str(exe),*map(str,args)],capture_output=True,text=True,timeout=5);assert run.returncode==0,run.stderr
   lines=run.stdout.splitlines();meta=list(map(int,lines[0].split()[1:]));cmds=[list(map(int,l.split()[1:])) for l in lines[1:]];assert meta[0]==len(cmds)
   mode,pages,ril,btm,e2h,stage=args
   assert meta[3]==1
   if mode!=1:
    assert meta[4]==19
    if btm:assert not cmds and meta[1]==0
    elif mode==2 or pages==0:assert not cmds and meta[1]==1 and meta[2]==17
    else:assert cmds and all(c[1]==17 and c[8]==0 for c in cmds)
   else:
    assert meta[4]==0 and cmds
    assert all(c[1]==23 if stage==1 else c[2]==31 for c in cmds)
   bad=sum(c[4]==c[5]==c[6]==0 for c in cmds) if ril else None
   cases.append(dict(version=version,page_shift=shift,kind=kind,args=args,stdout=run.stdout,commands=cmds,meta=meta,invalid_triples=bad,scope='original function chain with boundary doubles; no notifier registration or device'))
save('builds.json',builds);save('function_manifest.json',bodies);save('chain_results.json',cases)
save('summary.json',dict(builds=len(builds),executions=len(cases),old_invalid_combinations=sum(bool(c['invalid_triples']) for c in cases if c['version']=='old'),fixed_invalid_combinations=sum(bool(c['invalid_triples']) for c in cases if c['version']=='fixed'),new_kernel_boots=0,new_device_operations=0,independent_positive=0,independent_normal=0))
print((H/'summary.json').read_text())
