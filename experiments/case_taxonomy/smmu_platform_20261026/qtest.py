from pathlib import Path
import subprocess,json
H=Path(__file__).resolve().parent
cmd=['qemu-system-aarch64','-M','virt,iommu=smmuv3','-cpu','max','-m','128','-S','-display','none','-serial','none','-monitor','none','-nodefaults','-qtest','stdio']
request=''.join(f'readl {0x9050000+i*4:#x}\n' for i in range(6))
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:out,err=p.communicate(request,timeout=5)
except subprocess.TimeoutExpired:p.terminate();out,err=p.communicate(timeout=5)
(H/'qtest.json').write_text(json.dumps(dict(command=cmd,request=request,stdout=out,stderr=err,code=p.returncode),indent=2));print(out);print(err[-500:])
