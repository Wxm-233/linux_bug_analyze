"""Publish only after raw-observation verification; preserve prior chronology."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 result=json.loads((HERE/'results.json').read_text())
 assert len(result['observations'])==6
 before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
 for n,h in before.items():assert sha(ROOT/n)==h,n
 block=(HERE/'conclusion.md').read_text(encoding='utf-8')
 for name in before:
  p=ROOT/name;old=p.read_text(encoding='utf-8-sig');title=old.splitlines()[0]
  cut=old.index('\n## ')
  history=old[cut:].replace('## 当前下一操作：已有VT-d内核结果与自动核验衔接','## 历史下一操作（已由本轮Btrfs恢复安排覆盖）：VT-d核验',1)
  p.write_text(title+'\n\n文档维护：2026-10-23。用户已恢复WSL Btrfs；本轮完成四个历史内核构建、六次QEMU启动与真实挂载/持久布局对照。详见以下最新记录，后续历史“暂存Btrfs/转VT-d”不再代表当前优先级。\n\n'+block+'\n\n以下为历史记录，按以上最新停点解释。\n'+history,encoding='utf-8')
 log=ROOT/'日志/2026-10-23.md'
 with log.open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
 after={n:sha(ROOT/n) for n in before}
 (HERE/'notes_update.json').write_text(json.dumps({'before_sha256':before,'after_sha256':after},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Windows notes and daily log updated; WSL mirror sync pending')
if __name__=='__main__':main()
