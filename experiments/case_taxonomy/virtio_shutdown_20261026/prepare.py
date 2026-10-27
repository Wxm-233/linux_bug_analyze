from pathlib import Path
import subprocess,json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];rev='db191ba0c8564ff84877e5b1c9553e991feca239'
def sha(b):return hashlib.sha256(b).hexdigest()
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
if not (H/'notes_before.json').exists():
 (H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:sha((R/n).read_bytes()) for n in names}},ensure_ascii=False,indent=2))
 shutil.copyfile(R/'接口验证后续规划.md',H/'plan_before.md')
 shutil.copyfile(H.parent/'virtio_recycle_20261026/sync_work_notes.py',H/'sync_work_notes.py')
(H/'source').mkdir(exist_ok=True);rows=[]
for p in ['drivers/virtio/virtio.c','drivers/virtio/virtio_pci_modern.c','drivers/virtio/virtio_pci_common.c','drivers/virtio/virtio_mmio.c']:
 b=subprocess.check_output(['git','-C','/root/repos/linux','show',rev+':'+p]);blob=subprocess.check_output(['git','-C','/root/repos/linux','rev-parse',rev+':'+p],text=True).strip()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
 dest=p.replace('/','__');(H/'source'/dest).write_bytes(b);rows.append(dict(path=p,local=dest,blob=blob,sha256=sha(b)))
(H/'sources.json').write_text(json.dumps(dict(revision=rev,files=rows),indent=2));print('4 pinned sources verified')
