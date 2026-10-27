from pathlib import Path
import subprocess,json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];S=H/'source';S.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha((R/n).read_bytes()) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(H.parent/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
rev='db191ba0c8564ff84877e5b1c9553e991feca239';rows=[]
for name in ['drivers/virtio/virtio_input.c','drivers/virtio/virtio_ring.c','include/linux/virtio_config.h','include/linux/virtio.h','kernel/dma/mapping.c','kernel/dma/direct.h','kernel/dma/direct.c','kernel/dma/swiotlb.c','Documentation/core-api/dma-api-howto.rst','include/linux/slab.h','arch/arm64/mm/dma-mapping.c']:
 p=subprocess.run(['wsl.exe','-d','Ubuntu','--','git','-C','/root/repos/linux','show',rev+':'+name],capture_output=True);assert p.returncode==0,(name,p.stderr)
 blob=hashlib.sha1(b'blob '+str(len(p.stdout)).encode()+b'\0'+p.stdout).hexdigest();q=subprocess.run(['wsl.exe','-d','Ubuntu','--','git','-C','/root/repos/linux','rev-parse',rev+':'+name],capture_output=True);assert q.returncode==0 and q.stdout.decode().strip()==blob
 out=S/name.replace('/','__');out.write_bytes(p.stdout);rows.append(dict(path=name,file=out.name,blob=blob,sha256=sha(p.stdout),bytes=len(p.stdout)))
save('source_manifest.json',dict(revision=rev,files=rows));print('11 pinned parent sources verified')
