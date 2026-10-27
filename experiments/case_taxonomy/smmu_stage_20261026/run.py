from pathlib import Path
import json,hashlib,importlib.util,subprocess,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];S=H.parent/'smmu_chain_20261026/source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}))
shutil.copyfile(H.parent/'smmu_binding_20261026/sync_work_notes.py',H/'sync_work_notes.py')
sp=importlib.util.spec_from_file_location('probe',H.parent/'smmu_range_probe.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
driver=(S/'00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c').read_text();sva=(S/'03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c').read_text();header=(S/'02_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.h').read_text()
funcs=[m.function(driver,'static int arm_smmu_domain_finalise('),m.function(sva,'bool arm_smmu_master_sva_supported('),m.function(sva,'int arm_smmu_master_enable_sva('),m.function(driver,'static int arm_smmu_dev_enable_feature(')]
pre=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#define ARM_SMMU_DOMAIN_S1 0
#define ARM_SMMU_DOMAIN_S2 1
#define ARM_SMMU_DOMAIN_NESTED 2
#define ARM_SMMU_DOMAIN_BYPASS 3
#define IOMMU_DOMAIN_IDENTITY 1
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define VA_BITS 48
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
enum iommu_dev_features {IOMMU_DEV_FEAT_IOPF,IOMMU_DEV_FEAT_SVA};
enum io_pgtable_fmt {ARM_64_LPAE_S1,ARM_64_LPAE_S2};
struct arm_smmu_domain;
struct iommu_domain {unsigned type;unsigned long pgsize_bitmap;struct {unsigned long aperture_end;bool force_aperture;} geometry;struct arm_smmu_domain *owner;};
struct io_pgtable_ops {int x;};
struct arm_smmu_device {unsigned features;unsigned long ias,oas,pgsize_bitmap;void *dev;};
struct arm_smmu_domain {struct iommu_domain domain;struct arm_smmu_device *smmu;int stage;struct io_pgtable_ops *pgtbl_ops;};
struct arm_smmu_master {struct arm_smmu_device *smmu;bool sva_enabled,iopf_enabled;unsigned ssid_bits;};
struct device {struct arm_smmu_master *master;};
struct io_pgtable_cfg {unsigned long pgsize_bitmap,ias,oas;bool coherent_walk;void *tlb,*iommu_dev;};
static int failure,allocs,stage_calls,sva_lock,arm_smmu_flush_ops;static struct io_pgtable_ops ops;
static struct arm_smmu_domain *to_smmu_domain(struct iommu_domain *d){return d->owner;}
static struct arm_smmu_master *dev_iommu_priv_get(struct device *d){return d->master;}
static struct io_pgtable_ops *alloc_io_pgtable_ops(enum io_pgtable_fmt f,struct io_pgtable_cfg *c,void *cookie){(void)f;(void)cookie;allocs++;if(failure==1)return NULL;c->pgsize_bitmap=(1UL<<12)|(1UL<<21);return &ops;}
static void free_io_pgtable_ops(struct io_pgtable_ops *p){(void)p;}
static int arm_smmu_domain_finalise_s1(struct arm_smmu_domain*d,struct arm_smmu_master*m,struct io_pgtable_cfg*c){(void)d;(void)m;(void)c;stage_calls++;return failure==2?-ENOMEM:0;}
static int arm_smmu_domain_finalise_s2(struct arm_smmu_domain*d,struct arm_smmu_master*m,struct io_pgtable_cfg*c){return arm_smmu_domain_finalise_s1(d,m,c);}
static bool arm_smmu_master_iopf_supported(struct arm_smmu_master*m){(void)m;return true;}
static bool arm_smmu_master_sva_enabled(struct arm_smmu_master*m){return m->sva_enabled;}
static int arm_smmu_master_sva_enable_iopf(struct arm_smmu_master*m){(void)m;return failure==3?-EINVAL:0;}
'''
import re
for name in ['ARM_SMMU_FEAT_TRANS_S1','ARM_SMMU_FEAT_TRANS_S2','ARM_SMMU_FEAT_SVA','ARM_SMMU_FEAT_VAX','ARM_SMMU_FEAT_COHERENCY']:
 hit=re.search(r'^#define\s+'+name+r'\s+([^\n]+)',header,re.M);assert hit;pre+='\n#define '+name+' '+hit[1]
pre+='\n'
main=r'''
int main(int argc,char**argv){if(argc!=8)return 2;int identity=atoi(argv[1]),s1=atoi(argv[2]),s2=atoi(argv[3]),initial=atoi(argv[4]),cap=atoi(argv[5]),ssid=atoi(argv[6]);failure=atoi(argv[7]);
struct arm_smmu_device smmu={.features=(s1?ARM_SMMU_FEAT_TRANS_S1:0)|(s2?ARM_SMMU_FEAT_TRANS_S2:0)|(cap?ARM_SMMU_FEAT_SVA:0),.ias=48,.oas=48,.pgsize_bitmap=(1UL<<12)|(1UL<<21)};
struct arm_smmu_domain d={.smmu=&smmu,.stage=initial,.domain={.type=identity?IOMMU_DOMAIN_IDENTITY:0}};d.domain.owner=&d;
struct arm_smmu_master master={.smmu=&smmu,.ssid_bits=ssid};struct device dev={.master=&master};
int ret=arm_smmu_domain_finalise(&d.domain,&master);int enabled=ret?999:arm_smmu_dev_enable_feature(&dev,IOMMU_DEV_FEAT_SVA);
printf("%d %d %d %d %d %d %lu\n",ret,d.stage,enabled,master.sva_enabled,allocs,stage_calls,d.domain.pgsize_bitmap);return 0;}
'''
p=H/'stage_gate.c';p.write_text(pre+'\n'.join(funcs)+main);exe=H/'stage_gate.bin'
build=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p),'-o',str(exe)],capture_output=True,text=True)
save('build.json',dict(returncode=build.returncode,stderr=build.stderr,source_sha256=sha(p),functions=[dict(signature=f.split('{')[0],sha256=hashlib.sha256(f.encode()).hexdigest()) for f in funcs]))
assert build.returncode==0,build.stderr
rows=[]
for identity in [0,1]:
 for s1,s2 in [(1,0),(0,1),(1,1)]:
  for initial in [0,2]:
   for cap,ssid,failure in [(1,8,0),(0,8,0),(1,0,0),(1,8,1),(1,8,2),(1,8,3)]:
    args=[identity,s1,s2,initial,cap,ssid,failure];out=subprocess.check_output([str(exe),*map(str,args)],text=True);ret,stage,enable,active,allocs,stages,bitmap=map(int,out.split())
    if ret:assert enable==999 and not active
    elif not cap or not ssid or failure==3:assert enable==-22 and not active
    else:assert enable==0 and active
    if identity:assert stage==3 and allocs==0 and bitmap==0
    elif s1 and not s2:assert stage==0
    elif s2 and not s1:assert stage==1
    else:assert stage==initial
    rows.append(dict(args=args,stdout=out,finalise=ret,stage=stage,feature_enable=enable,sva_enabled=bool(active),scope='original branch functions; allocator, final-stage and IOPF bodies are doubles; hypothetical feature tuples not certified hardware'))
save('results.json',rows)
save('summary.json',dict(executions=len(rows),non_s1_feature_enabled=sum(r['sva_enabled'] and r['stage']!=0 for r in rows),claim='local feature enable does not establish S1; not proof of successful SVA bind or a new defect',new_kernel_boots=0,new_model_calls=0))
print((H/'summary.json').read_text())
