from pathlib import Path
import subprocess,json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}))
shutil.copyfile(H.parent/'smmu_chain_20261026/sync_work_notes.py',H/'sync_work_notes.py')
out=H/'source';out.mkdir();manifest=[]
for path in ['drivers/iommu/iommu-sva.c','drivers/iommu/iommu.c','drivers/iommu/io-pgtable.c','mm/mmu_notifier.c','include/linux/iommu.h']:
 rev='0bb80ecc33a8fb5a682236443c1e740d5c917d1d'
 raw=subprocess.check_output(['git','-C','/root/repos/linux','show',rev+':'+path]);blob=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',rev+':'+path],text=True).strip()
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob
 p=out/path.replace('/','__');p.write_bytes(raw);manifest.append(dict(path=path,revision=rev,blob=blob,sha256=sha(p)))
save('source_manifest.json',manifest)
print('Five pinned upstream source files collected; no model call.')
