from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=R/'模型调用测试/2026-10-26/virtio_dma_chain';new=R/'模型调用测试/2026-10-26/virtio_dma_chain_retry'
new.mkdir(parents=True,exist_ok=False);shutil.copyfile(old/'prompt.md',new/'prompt.md');assert sha(old/'prompt.md')==sha(new/'prompt.md')
(H/'authorization.json').write_text(json.dumps(dict(user_authorized_retry=True,reason='User reports switching ccSwitch back to Claude and explicitly requests another attempt',same_prompt_sha256=sha(new/'prompt.md'),prior_receipt_sha256=sha(old/'receipt.json'),route='project explicit native Claude Code 2.1.301 / AWS-Claude-Opus-5.5; no ccSwitch configuration modified',retry_directory=str(new)),ensure_ascii=False,indent=2),encoding='utf-8')
(H/'notes_before.json').write_text(json.dumps({'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(H.parent/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
print('New attempt prepared; exact prompt SHA verified; old attempt retained.')
