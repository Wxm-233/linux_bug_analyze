from pathlib import Path
import hashlib,json,subprocess,shutil,re
H=Path(__file__).resolve().parent; R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
if not (H/'notes_before.json').exists():
 save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(H.parent/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
src=H.parent/'smmu_binding_20261026/source/drivers__iommu__iommu.c'
s=src.read_text(); manifest=[]
def extract(name):
 start=re.search(r'^(?:static )?(?:int|void) '+name+r'\(',s,re.M).start();pos=start;a=s.index('{',pos);depth=1;b=a+1
 while depth:
  depth+=(s[b]=='{')-(s[b]=='}');b+=1
 out=s[start:b];manifest.append({'function':name,'line':s.count('\n',0,start)+1,'sha256':hashlib.sha256(out.encode()).hexdigest()});return out
names=['__iommu_set_group_pasid','__iommu_remove_group_pasid','iommu_attach_device_pasid','iommu_detach_device_pasid']
# Exact function bodies; list, lock, xarray, device and callback implementations below are doubles.
parts=[extract(n) for n in names]
head=r'''
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <assert.h>
typedef unsigned ioasid_t;
struct device {int id;};
struct iommu_domain;
struct domain_ops {int (*set_dev_pasid)(struct iommu_domain*,struct device*,ioasid_t);};
struct iommu_domain {struct domain_ops *ops;};
struct group_device {struct device *dev;};
struct iommu_group {int mutex; void *pasid_array;struct group_device devices[3];};
struct iommu_ops {void (*remove_dev_pasid)(struct device*,ioasid_t);};
static struct iommu_group g;
static int fail=-1,no_group,insert_error,active[3],calls,removes;
#define GFP_KERNEL 0
#define for_each_group_device(group,device) for(device=(group)->devices;device<(group)->devices+3;device++)
#define WARN_ON(x) assert(!(x))
static void event(const char *name,int id){printf("%s %d %d %d\n",name,id,g.pasid_array!=NULL,g.mutex);}
static void mutex_lock(int *p){assert(!*p);*p=1;}
static void mutex_unlock(int *p){assert(*p);*p=0;}
static struct iommu_group *iommu_group_get(struct device*d){(void)d;return no_group?NULL:&g;}
static void iommu_group_put(struct iommu_group*p){assert(p==&g);}
static void *xa_cmpxchg(void **p,ioasid_t id,void *old,void *v,int flags){(void)id;(void)old;(void)flags;if(insert_error)return(void*)-12L;void*r=*p;if(!r)*p=v;event("publish",-1);return r;}
static int xa_err(void*p){return p==(void*)-12L?-12:0;}
static void *xa_erase(void **p,ioasid_t id){(void)id;void*r=*p;event("erase",-1);*p=NULL;return r;}
static int set(struct iommu_domain*d,struct device*v,ioasid_t id){(void)id;assert(g.mutex&&g.pasid_array==d);calls++;event("set",v->id);if(v->id==fail)return-EIO;active[v->id]=1;return 0;}
static void remove_one(struct device*v,ioasid_t id){(void)id;assert(g.mutex&&g.pasid_array);removes++;event("remove",v->id);active[v->id]=0;}
static struct iommu_ops ops={remove_one};
static const struct iommu_ops *dev_iommu_ops(struct device*d){(void)d;return &ops;}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==2);int mode=atoi(argv[1]);struct device ds[3]={{0},{1},{2}};struct domain_ops dop={set};struct iommu_domain domain={&dop},other={&dop};for(int i=0;i<3;i++)g.devices[i].dev=&ds[i];
if(mode>=1&&mode<=3)fail=mode-1;
if(mode==4)g.pasid_array=&other;
if(mode==5)insert_error=1;
if(mode==6)no_group=1;
if(mode==7)dop.set_dev_pasid=NULL;
int ret=iommu_attach_device_pasid(&domain,&ds[0],7);
if(mode==8){assert(!ret);iommu_detach_device_pasid(&domain,&ds[0],7);}
assert(!g.mutex);
if(mode>=1&&mode<=3){assert(ret==-EIO&&calls==mode&&removes==3&&!g.pasid_array);}
if(mode==0)assert(!ret&&calls==3&&removes==0&&g.pasid_array==&domain);
if(mode==4)assert(ret==-EBUSY&&!calls&&!removes&&g.pasid_array==&other);
if(mode==5)assert(ret==-ENOMEM&&!calls&&!removes&&!g.pasid_array);
if(mode==6)assert(ret==-ENODEV&&!calls&&!removes);
if(mode==7)assert(ret==-EOPNOTSUPP&&!calls&&!removes);
if(mode==8)assert(!ret&&calls==3&&removes==3&&!g.pasid_array);
printf("result %d %d %d %d %d\n",ret,calls,removes,g.pasid_array!=NULL,active[0]+active[1]+active[2]);return 0;}
'''
(H/'transaction.c').write_text(head+'\n'.join(parts)+tail)
save('function_manifest_fixed.json',{'source':str(src.relative_to(R)),'source_sha256':sha(src),'functions':manifest,'limit':'Original functions; callbacks, xarray, locks, list and devices are doubles, no concurrency.'})
wh='/mnt/d/homework/software/linux_bug_analyze/'+str(H.relative_to(R)).replace('\\','/')
cmd=['wsl.exe','-d','Ubuntu','--','gcc','-std=gnu11','-Wall','-Wextra','-Werror',wh+'/transaction.c','-o',wh+'/transaction.bin']
p=subprocess.run(cmd,capture_output=True);save('build_fixed.json',dict(command=cmd,returncode=p.returncode,stdout=p.stdout.decode('utf-8',errors='replace'),stderr_hex=p.stderr.hex()));assert p.returncode==0,p.stderr
rows=[]
for i in range(9):
 p=subprocess.run(['wsl.exe','-d','Ubuntu','--',wh+'/transaction.bin',str(i)],capture_output=True,text=True,encoding='utf-8',errors='replace')
 rows.append(dict(mode=i,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0,p.stderr
save('results.json',rows)
print('1 original-function build; 9 transaction scenarios passed')
