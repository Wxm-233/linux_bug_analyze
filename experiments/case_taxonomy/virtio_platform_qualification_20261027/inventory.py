from pathlib import Path
import subprocess,shutil,json,os
H=Path(__file__).resolve().parent
def cmd(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=25);return dict(code=p.returncode,stdout=p.stdout[:6000],stderr=p.stderr[:600])
data=dict(tools={n:shutil.which(n) for n in ['qemu-system-aarch64','qemu-system-x86_64','aarch64-linux-gnu-gcc','aarch64-linux-gnu-gdb','gdb','dtc','cpio','busybox','pahole','readelf']},kernel_git=cmd(['git','-C','/root/repos/linux','rev-parse','HEAD']),parent_makefile=cmd(['git','-C','/root/repos/linux','show','db191ba0c8564ff84877e5b1c9553e991feca239:Makefile']),kvm_present=Path('/dev/kvm').exists(),host_uname=cmd(['uname','-a']))
cache=Path('/root/.cache/linux-bug-analyze');entries=[]
if cache.exists():
 for p in sorted(cache.iterdir()):
  if any(x in p.name for x in ['btrfs','virtio','arm64','smmu']):
   children=[]
   if p.is_dir():children=[q.name for q in sorted(p.iterdir())][:35]
   entries.append(dict(path=str(p),children=children))
data['relevant_cache_directories']=entries
builds=[]
for root in ['/root/.cache/linux-bug-analyze','/root/repos/linux','/root/lba-vtd-build']:
 p=Path(root)
 if not p.exists():continue
 if root.endswith('linux-bug-analyze'):
  candidates=[p,*[q for q in p.glob('*') if q.is_dir() and any(t in q.name for t in ['btrfs','virtio','arm64'])]]
  candidates += [q for parent in list(candidates)[1:] for q in parent.glob('*') if q.is_dir()]
 else:candidates=[p]
 for q in candidates:
  for suffix in ['.config','arch/arm64/boot/Image','vmlinux','usr/gen_init_cpio','busybox','initramfs.cpio.gz']:
   f=q/suffix
   if f.is_file():builds.append(dict(path=str(f),bytes=f.stat().st_size))
data['available_build_material']=builds
for tool in ['qemu-system-aarch64','aarch64-linux-gnu-gcc']:
 if shutil.which(tool):data[tool+'_version']=cmd([tool,'--version'])
(H/'environment.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
