from pathlib import Path
import subprocess,json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024')
build=BASE/'parent/build'
out=HERE/'compiled';out.mkdir(exist_ok=False)
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=json.loads((raw/'manifest.json').read_text())[0]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(build/'arch/arm64/boot/Image')==manifest['image_sha256']
assert sha(raw/'parent/super.i')==manifest['artifacts']['super.i']
extra='\nconst unsigned long lba_offsets[] = {__builtin_offsetof(struct btrfs_fs_info, super_copy), __builtin_offsetof(struct btrfs_fs_info, sectorsize), __builtin_offsetof(struct btrfs_fs_info, max_inline), __builtin_offsetof(struct btrfs_super_block, sectorsize)};\n'
p=out/'offsets.i';p.write_bytes((raw/'parent/super.i').read_bytes()+extra.encode())
cmd=['aarch64-linux-gnu-gcc','-x','cpp-output','-S','-O2','-fno-PIE','-fno-strict-aliasing','-mgeneral-regs-only','-mabi=lp64','-mbranch-protection=none','-fno-stack-protector','-o',str(out/'offsets.s'),str(p)]
done=subprocess.run(cmd,capture_output=True);(out/'compile.log').write_bytes(done.stdout+done.stderr);done.check_returncode()
asm=(out/'offsets.s').read_text();tail=asm.split('lba_offsets:',1)[1]
import re
offsets=[int(x) for x in re.findall(r'^\s*\.xword\s+(\d+)',tail,re.M)[:4]]
assert len(offsets)==4
nm=subprocess.check_output(['aarch64-linux-gnu-nm',str(build/'vmlinux')]).decode()
symbols={s.split()[2]:int(s.split()[0],16) for s in nm.splitlines() if len(s.split())==3}
entry=symbols['btrfs_parse_options']
(out/'parse.disasm').write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--disassemble=btrfs_parse_options',str(build/'vmlinux')]))
initrd=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/initramfs.cpio.gz')
# Resolve only previously recorded initrd identity, without guessing a replacement.
candidates=list(Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023').glob('*'))
initrds=[p for p in candidates if p.is_file() and p.stat().st_size<10000000 and sha(p)==manifest['initrd_sha256']]
assert len(initrds)==1,initrds
record=dict(offsets=dict(zip(['super_pointer','cache','max_inline','disk_sector'],offsets)),entry=entry,
 image=str(build/'arch/arm64/boot/Image'),image_sha256=manifest['image_sha256'],vmlinux_sha256=sha(build/'vmlinux'),
 initrd=str(initrds[0]),initrd_sha256=manifest['initrd_sha256'],blank=str(BASE/'blank.img'),blank_sha256=sha(BASE/'blank.img'))
(HERE/'prepared.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
