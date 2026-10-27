from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
if (H/'notes_before.json').exists():raise RuntimeError('preserve this round')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(R/'接口验证后续规划.md',H/'plan_before.md')
shutil.copyfile(H.parent/'virtio_shutdown_20261026/sync_work_notes.py',H/'sync_work_notes.py')
print('round snapshots saved')
