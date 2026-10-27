"""Historical unmodified kernels, isolated QEMU disks; all commands retained."""
import subprocess as sp, os, json, hashlib, time, gzip, shutil, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023')
OUT=HERE.parents[2]/'analysis_out'/'btrfs-mount-resume-20261023'
REVS={'parent':'0d977e0eba234e01a60bdde27314dc21374201b3','fix':'6f93e834fa7c5faa0372e46828b4b2a966ac61d7'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(args,name,timeout=1200):
 logs=OUT/'commands';logs.mkdir(parents=True,exist_ok=True)
 idx=len(list(logs.glob('*.json'))); stem=logs/f'{idx:03d}-{name}'
 row={'argv':list(map(str,args)),'started':time.time()};save(stem.with_suffix('.json'),row)
 print(name,flush=True)
 with stem.with_suffix('.log').open('wb') as f:
  try:rc=sp.run(row['argv'],stdout=f,stderr=sp.STDOUT,timeout=timeout,env=dict(os.environ,LC_ALL='C')).returncode
  except sp.TimeoutExpired:rc=124
 row.update(returncode=rc,seconds=time.time()-row['started']);save(stem.with_suffix('.json'),row)
 if rc:raise RuntimeError(f'{name}: {rc}; {stem.with_suffix(".log")}')
 return stem.with_suffix('.log')
def main():
 OUT.mkdir(parents=True,exist_ok=True);BASE.mkdir(parents=True,exist_ok=True)
 run(['mkfs.btrfs','--version'],'tool_version')
 for mode,rev in REVS.items():
  tree=BASE/mode/'source'
  if not tree.exists():
   tree.mkdir(parents=True); archive=BASE/(mode+'.tar')
   run(['git','-C','/root/repos/linux','archive','-o',archive,rev],'archive_'+mode)
   run(['tar','-xf',archive,'-C',tree],'extract_'+mode)
   (tree.parent/'revision').write_text(rev)
  assert (tree.parent/'revision').read_text()==rev
  for page in sys.argv[1:] or ['64']:
   build=BASE/f'{mode}-{page}k'; dest=OUT/f'{mode}-{page}k';dest.mkdir(exist_ok=True)
   make=['make','-C',tree,f'O={build}','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-']
   if not (build/'arch/arm64/boot/Image').exists():
    run(make+['allnoconfig'],f'config_{mode}_{page}')
    enabled=['ARM64_'+page+'K_PAGES','ARM64_VA_BITS_48','ARCH_VIRT','ARM_GIC','ARM_GIC_V3','SERIAL_AMBA_PL011','SERIAL_AMBA_PL011_CONSOLE','ARM_ARCH_TIMER','BLK_DEV_INITRD','RD_GZIP','BINFMT_ELF','PRINTK','TTY','DEVTMPFS','PROC_FS','SYSFS','FUTEX','MULTIUSER','POSIX_TIMERS','BLOCK','VIRTIO','VIRTIO_MMIO','VIRTIO_BLK','BTRFS_FS','CRC32C','CRYPTO_CRC32C']
    enabled+=['BLK_DEV','VIRTIO_MENU']
    edits=[tree/'scripts/config','--file',build/'.config']
    for k in enabled:edits+=['--enable',k]
    for k in ['ARM64_'+('4' if page=='64' else '64')+'K_PAGES','ARM64_16K_PAGES','ARM64_VA_BITS_39','ARM64_VA_BITS_42','ARM64_VA_BITS_47','ARM64_VA_BITS_52','MODULES','LOCALVERSION_AUTO']:edits+=['--disable',k]
    edits+=['--set-str','LOCALVERSION','-btrfs-contract']
    run(edits,'config_edit');run(make+['olddefconfig'],'olddefconfig')
    config=(build/'.config').read_text()
    for k in ['ARM64_'+page+'K_PAGES','BTRFS_FS','VIRTIO_BLK','VIRTIO_MMIO','DEVTMPFS','BLK_DEV_INITRD','SERIAL_AMBA_PL011_CONSOLE']:assert f'CONFIG_{k}=y\n' in config,k
    run(make+['-j6','Image'],'kernel_build',1800)
   shutil.copyfile(build/'.config',dest/'kernel.config')
   run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra',HERE/'init.c','-o',build/'pid1.elf'],'init_build')
   listing=build/'initramfs.list';listing.write_text('dir /dev 755 0 0\nnod /dev/console 600 0 0 c 5 1\n'+f'file /init {build}/pid1.elf 755 0 0\n')
   initrd=build/'initrd.gz';initrd.write_bytes(gzip.compress(sp.check_output([str(build/'usr/gen_init_cpio'),str(listing)]),mtime=0))
   image=build/'arch/arm64/boot/Image'
   save(dest/'build.json',{'revision':rev,'image':str(image),'image_sha256':sha(image),'config_sha256':sha(build/'.config'),'init_sha256':sha(build/'pid1.elf'),'init_source_sha256':sha(HERE/'init.c'),'instrumentation':False})
   for sector in (['65536','4096'] if page=='64' else ['4096']):
    d=dest/('sector'+sector);d.mkdir(exist_ok=True);disk=BASE/f'{mode}-{page}k-sector{sector}.img'
    if (d/'boot.log').exists():continue
    assert not disk.exists(),str(disk)
    with disk.open('xb') as f:f.truncate(512*1024*1024)
    run(['mkfs.btrfs','-f','-s',sector,'-n','65536','-m','single','-d','single','-O','^free-space-tree',disk],'mkfs')
    p=run(['btrfs','inspect-internal','dump-super',disk],'super');shutil.copyfile(p,d/'super.txt')
    cmd=['qemu-system-aarch64','-machine','virt','-cpu','max','-m','1024','-smp','1','-nographic','-no-reboot','-kernel',image,'-initrd',initrd,'-append','console=ttyAMA0 rdinit=/init panic=-1','-drive',f'file={disk},format=raw,if=none,id=fs','-device','virtio-blk-device,drive=fs','-nic','none']
    p=run(cmd,'boot',180);shutil.copyfile(p,d/'boot.log')
    p=run(['btrfs','inspect-internal','dump-tree','-t','5',disk],'tree');shutil.copyfile(p,d/'tree.txt')
    boot=(d/'boot.log').read_text();save(d/'result.json',{'completed':'EXPERIMENT_DONE failures=0' in boot,'page':page,'sector':sector,'disk':str(disk),'disk_sha256':sha(disk)})
    assert 'EXPERIMENT_DONE failures=0' in boot, str(d/'boot.log')
if __name__=='__main__':main()
