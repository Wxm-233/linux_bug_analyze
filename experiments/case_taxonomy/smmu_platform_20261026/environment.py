from pathlib import Path
import subprocess,json
H=Path(__file__).resolve().parent
rows=[]
for cmd in [['uname','-a'],['qemu-system-aarch64','--version'],['qemu-system-aarch64','-machine','virt,help']]:
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=15);rows.append(dict(command=cmd,code=p.returncode,stdout=p.stdout,stderr=p.stderr))
for path in ['/sys/class/iommu','/sys/bus/pci/devices']:
 p=Path(path);rows.append(dict(path=path,exists=p.exists(),entries=[v.name for v in p.iterdir()] if p.exists() else []))
cmd=['qemu-system-aarch64','-M','virt,iommu=smmuv3','-cpu','max','-m','128','-S','-display','none','-serial','none','-monitor','stdio','-nodefaults']
p=subprocess.run(cmd,input='info mtree\nquit\n',capture_output=True,text=True,timeout=20)
rows.append(dict(command=cmd,stdin='info mtree; quit',code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(H/'environment.json').write_text(json.dumps(rows,indent=2));print(p.stdout)
