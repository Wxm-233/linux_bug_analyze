from pathlib import Path
import subprocess,json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(H.parent/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
src=H.parent/'smmu_stage_20261026/address_results.json';source=json.loads(src.read_text());cases=[]
for r in source['cases']:cases.append(dict(name=r['version']+'_'+str(r['pages']),words=[[int(w,16) for w in line.split()] for line in r['words'].splitlines()],reserved=r['reserved_commands']))
cases += [dict(name='sync_only',words=[],reserved=0),dict(name='unknown_opcode',words=[[0xff,0]],reserved=None)]
base=0x9050000;ram=0x40010000;rows=[]
cmd=['qemu-system-aarch64','-M','virt,iommu=smmuv3','-cpu','max','-m','128','-S','-display','none','-serial','none','-monitor','none','-nodefaults','-qtest','stdio']
for case in cases:
 words=case['words']+[[0x46,0]];requests=[]
 def req(s):requests.append(s)
 for i,pair in enumerate(words):
  for j,w in enumerate(pair):req(f'writeq {ram+i*16+j*8:#x} {w:#x}')
 for i,pair in enumerate(words):
  for j,w in enumerate(pair):req(f'readq {ram+i*16+j*8:#x}')
 req(f'writeq {base+0x90:#x} {ram|6:#x}')
 req(f'writel {base+0x20:#x} 0x8');req(f'readl {base+0x24:#x}')
 req(f'writel {base+0x98:#x} {len(words):#x}')
 for off in [0x98,0x9c,0x60,0x64]:req(f'readl {base+off:#x}')
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 terminated=False
 try:out,err=p.communicate('\n'.join(requests)+'\n',timeout=2)
 except subprocess.TimeoutExpired:
  terminated=True;p.terminate();out,err=p.communicate(timeout=5)
 replies=[l for l in out.splitlines() if l.startswith('OK')]
 row=dict(**case,requests=requests,stdout=out,stderr=err,returncode=p.returncode,terminated_after_capture=terminated)
 save(case['name']+'.json',row)
 assert len(replies)==len(requests),(case['name'],out,err)
 reads=[int(rep.split()[1],16) for request,rep in zip(requests,replies) if request.startswith('read')]
 assert reads[:2*len(words)]==[w for pair in words for w in pair]
 ack,prod,cons,ge,gn=reads[-5:];assert ack==8 and prod==len(words)
 row=dict(name=case['name'],reserved=case['reserved'],commands=len(words),cr0ack=ack,prod=prod,cons=cons,gerror=ge,gerrorn=gn,cons_index=cons&127,error=(cons>>24)&127)
 rows.append(row)
save('results.json',dict(command=cmd,input_sha256=sha(src),cases=rows));print(json.dumps(rows,indent=2))
