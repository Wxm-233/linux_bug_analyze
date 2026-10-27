"""Freeze the existing method before collecting the same-family fix control."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
old=HERE.parent/'btrfs_kernel_watch_20261025'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[old/'run.py',old/'verify.py',old/'prepared.json',old/'verified.json',old/'runtime/rsp.jsonl',
       ROOT/'linux_bug_analyze/linux_bug_analyze/btrfs_watch_facts.py',
       ROOT/'linux_bug_analyze/linux_bug_analyze/btrfs_runtime_facts.py',
       HERE.parent/'btrfs_consumer_observation_20261024/observations.py']
(HERE/'frozen_inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in files},indent=2)+'\n',encoding='utf-8')
text=(old/'run.py').read_text(encoding='utf-8')
text=text.replace('btrfs-kernel-watch-20261025.img','btrfs-fix-watch-20261025.img')
(HERE/'run.py').write_text(text,encoding='utf-8')
text=(old/'verify.py').read_text(encoding='utf-8').replace('kernel-watch-parent','kernel-watch-fix').replace("['observations'][0]","['observations'][1]")
(HERE/'verify.py').write_text(text,encoding='utf-8')
text=(old/'prepare.py').read_text(encoding='utf-8').replace("BASE/'parent/build'","BASE/'fix/build'").replace("read_text())[0]","read_text())[1]").replace("raw/'parent/super.i'","raw/'fix/super.i'")
start=text.index("initrd=Path(");end=text.index('record=dict(',start)
text=text[:start]+"initrd=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/fix-64k/initrd.gz')\nassert sha(initrd)==manifest['initrd_sha256']\n"+text[end:]
text=text.replace("str(initrds[0])","str(initrd)")
(HERE/'prepare.py').write_text(text,encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
(HERE/'notes_before.json').write_text(json.dumps(dict(before_sha256={n:sha(ROOT/n) for n in names}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Method frozen; only fix source/build, disk name, and baseline context selected')
