from pathlib import Path
import json,subprocess,re,hashlib
H=Path(__file__).resolve().parent
env=json.loads((H/'environment.json').read_text());mtree=env[-1]['stdout'];m=re.search(r'([0-9a-f]{16})-[0-9a-f]+ .*: arm-smmuv3',mtree);assert m
base=int(m[1],16);cmd=env[-1]['command'];query=f'xp /6wx {base:#x}\nquit\n'
p=subprocess.run(cmd,input=query,capture_output=True,text=True,timeout=20);assert p.returncode==0
words=[]
for line in p.stdout.splitlines():
 if re.match(r'^0*[0-9a-f]+:',line):words+=re.findall(r'0x([0-9a-f]{8})',line)
assert len(words)==6,(words,p.stdout)
v=list(map(lambda x:int(x,16),words));h=H.parent/'smmu_chain_20261026/source/02_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.h'
result=dict(command=cmd,input=query,stdout=p.stdout,stderr=p.stderr,base=hex(base),registers=[hex(x) for x in v],decode_header_sha256=hashlib.sha256(h.read_bytes()).hexdigest(),decoded={'S1P':bool(v[0]&2),'S2P':bool(v[0]&1),'COHACC':bool(v[0]&16),'ASID16':bool(v[0]&(1<<12)),'ATS':bool(v[0]&(1<<10)),'SSID_bits':(v[1]>>6)&31,'RIL':bool(v[3]&(1<<10)),'granule4k':bool(v[5]&16),'granule16k':bool(v[5]&32),'granule64k':bool(v[5]&64),'oas_encoding':v[5]&7})
(H/'registers.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['decoded']))
