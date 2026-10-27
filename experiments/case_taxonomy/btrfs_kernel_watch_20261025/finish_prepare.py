from pathlib import Path
import subprocess,re,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024')
build=BASE/'parent/build';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/manifest.json').read_text())[0]
asm=(HERE/'compiled/offsets.s').read_text().split('lba_offsets:',1)[1]
offsets=[int(x) for x in re.findall(r'^\s*\.xword\s+(\d+)',asm,re.M)[:4]];assert len(offsets)==4
nm=subprocess.check_output(['aarch64-linux-gnu-nm',str(build/'vmlinux')]).decode()
entry=[int(s.split()[0],16) for s in nm.splitlines() if s.endswith(' btrfs_parse_options')][0]
initrd=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/fix-64k/initrd.gz')
assert sha(initrd)==manifest['initrd_sha256']
assert sha(build/'arch/arm64/boot/Image')==manifest['image_sha256']
record=dict(offsets=dict(zip(['super_pointer','cache','max_inline','disk_sector'],offsets)),entry=entry,
 image=str(build/'arch/arm64/boot/Image'),image_sha256=manifest['image_sha256'],vmlinux_sha256=sha(build/'vmlinux'),
 initrd=str(initrd),initrd_sha256=manifest['initrd_sha256'],blank=str(BASE/'blank.img'),blank_sha256=sha(BASE/'blank.img'),
 preparation_note='First compile succeeded; initial initrd search at cache top level failed. Correct archived path recovered from prior run.py; no recompilation.')
(HERE/'prepared.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
