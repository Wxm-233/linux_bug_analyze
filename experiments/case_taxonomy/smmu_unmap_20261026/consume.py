from pathlib import Path
import subprocess,json,hashlib
H=Path(__file__).resolve().parent;O=H.parent/'smmu_chain_20261026'
observed=json.loads((H/'observed_results.json').read_text())['cases'];enc=O/'cmd_build_projection.bin';assert hashlib.sha256(enc.read_bytes()).hexdigest()==json.loads((O/'encoding_results.json').read_text())['binary_sha256']
builds=[];rows=[]
for version in ['old','fixed']:
 for shift in [12,14,16]:
  original=O/f'{version}_{shift}.c';s=original.read_text();s=s[:s.index('int main(')]+r'''
int main(int argc,char**argv){if(argc!=5)return 2;unsigned long a=strtoul(argv[1],0,0),n=strtoul(argv[2],0,0),g=strtoul(argv[3],0,0);int stage=atoi(argv[4]);struct arm_smmu_device smmu={.features=ARM_SMMU_FEAT_RANGE_INV};struct arm_smmu_domain d={.smmu=&smmu,.stage=stage,.domain={.pgsize_bitmap=PAGE_SIZE|(PAGE_SIZE<<(PAGE_SHIFT-3))},.s1_cfg={.cd={.asid=23}},.s2_cfg={.vmid=31}};
arm_smmu_tlb_inv_walk(a,n,g,&d);
for(unsigned i=0;i<recorded_count;i++){struct arm_smmu_cmdq_ent*c=&recorded[i];printf("%u %d %d %lu %lu %lu %lu %lu %u\n",c->opcode,c->tlbi.asid,c->tlbi.vmid,c->tlbi.addr,c->tlbi.ttl,c->tlbi.num,c->tlbi.scale,c->tlbi.tg,c->tlbi.leaf);}return 0;}
'''
  p=H/f'{version}_{shift}_walk.c';p.write_text(s);exe=p.with_suffix('.bin');q=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function',f'-DPAGE_SHIFT={shift}',str(p),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr;builds.append(dict(source=p.name,parent_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),stderr=q.stderr))
  selected=next(r for r in observed if r['shift']==shift and r['mode']==1 and r['coherent']==0)
  for line in selected['stdout'].splitlines():
   if not line.startswith('WALK '):continue
   a,n,g=map(int,line.split()[1:])
   for stage in [1,2]:
    raw=subprocess.check_output([str(exe),str(a),str(n),str(g),str(stage)],text=True)
    encoded=subprocess.run([str(enc)],input=raw,capture_output=True,text=True,check=True).stdout
    cursor=a
    for line2 in encoded.splitlines():
     w0,w1=(int(x,16) for x in line2.split());num=(w0>>12)&31;scale=(w0>>20)&31;tg=(w1>>10)&3;ttl=(w1>>8)&3;addr=w1&(~4095)
     assert w0&255==(0x12 if stage==1 else 0x2a);assert ttl==0 and w1&1==0 and tg==(shift-10)//2
     assert addr==cursor and not(num==scale==ttl==0);cursor+=((num+1)<<scale)*(1<<shift)
    assert cursor==a+n
    rows.append(dict(version=version,shift=shift,logical_stage=stage,address=a,size=n,granule=g,raw=raw,words=encoded,coverage='exact',ttl=0,scope='callback argument handoff; separate objects, no real device'))
(H/'consume_results.json').write_text(json.dumps(dict(builds=builds,cases=rows),indent=2));print('6 consumer builds / 24 walker-derived calls / 24 encoding calls passed')
