from pathlib import Path
import json,shutil,subprocess as sp,importlib.util,difflib,sys
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('prior',HERE.parent/'btrfs_mount_resume_20261023/run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
r.OUT=PROJECT/'analysis_out/btrfs-consumer-observation-20261024'
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024')
OLD=PROJECT/'analysis_out/btrfs-mount-resume-20261023'
OLD_CACHE=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023')
ORIGINAL='''\t\t\t\t\tinfo->max_inline = min_t(u64,
\t\t\t\t\t\tinfo->max_inline,
\t\t\t\t\t\tinfo->sectorsize);'''
REPLACEMENT='''\t\t\t\t\tu64 lba_request = info->max_inline;
\t\t\t\t\tu32 lba_cache = info->sectorsize;
\t\t\t\t\tu64 lba_result = min_t(u64, lba_request, lba_cache);
\t\t\t\t\tstruct btrfs_super_block *lba_super;
\t\t\t\t\tu32 lba_disk;

\t\t\t\t\tinfo->max_inline = lba_result;
\t\t\t\t\tlba_super = info->super_copy;
\t\t\t\t\tlba_disk = btrfs_super_sectorsize(lba_super);
\t\t\t\t\tbtrfs_info(info,
\t\t\t\t\t\t"LBA_CLAMP info=%px super=%px fsid=%pU request=%llu cache=%u disk=%u result=%llu",
\t\t\t\t\t\tinfo, lba_super, lba_super->fsid,
\t\t\t\t\t\tlba_request, lba_cache, lba_disk, lba_result);'''
def prepare():
 r.OUT.mkdir(parents=True,exist_ok=True);BASE.mkdir(parents=True,exist_ok=True)
 assert not (r.OUT/'prepared.json').exists()
 rows=[]
 for mode,rev in r.REVS.items():
  tree=BASE/mode/'source';tree.mkdir(parents=True)
  archive=BASE/(mode+'.tar');r.run(['git','-C','/root/repos/linux','archive','-o',archive,rev],'archive_'+mode)
  r.run(['tar','-xf',archive,'-C',tree],'extract_'+mode)
  p=tree/'fs/btrfs/super.c';original=p.read_text();assert original.count(ORIGINAL)==1
  changed=original.replace(ORIGINAL,REPLACEMENT);p.write_text(changed)
  dest=r.OUT/mode;dest.mkdir();(dest/'super.original.c').write_text(original);(dest/'super.observed.c').write_text(changed)
  patch=''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='a/fs/btrfs/super.c',tofile='b/fs/btrfs/super.c'))
  (dest/'observation.patch').write_text(patch)
  old=json.loads((OLD/f'{mode}-64k/build.json').read_text());assert r.sha(Path(old['image']))==old['image_sha256']
  build=BASE/mode/'build';build.mkdir();shutil.copyfile(OLD/f'{mode}-64k/kernel.config',build/'.config')
  assert r.sha(build/'.config')==old['config_sha256']
  rows.append({'mode':mode,'revision':rev,'tree':str(tree),'build':str(build),'source_before_sha256':r.sha(dest/'super.original.c'),'source_after_sha256':r.sha(p),'patch_sha256':r.sha(dest/'observation.patch'),'baseline_build':old})
 r.save(r.OUT/'prepared.json',rows)
def execute():
 assert (HERE/'observation_review.md').exists()
 assert not (r.OUT/'manifest.json').exists()
 rows=json.loads((r.OUT/'prepared.json').read_text());initrd=OLD_CACHE/'fix-64k/initrd.gz'
 initbin=OLD_CACHE/'fix-64k/pid1.elf';old=json.loads((OLD/'fix-64k/build.json').read_text())
 assert r.sha(initbin)==old['init_sha256']
 # Verify the archived cpio actually contains the same init binary.
 raw=sp.check_output(['gzip','-dc',str(initrd)])
 extracted=sp.run(['cpio','-i','--to-stdout','init'],input=raw,capture_output=True,check=True).stdout
 assert extracted==initbin.read_bytes()
 blank=BASE/'blank.img'
 with blank.open('xb') as f:f.truncate(512*1024*1024)
 r.run(['mkfs.btrfs','-f','-s','65536','-n','65536','-m','single','-d','single','-O','^free-space-tree',blank],'mkfs')
 blank_sha=r.sha(blank);result=[]
 for row in rows:
  mode=row['mode'];tree=Path(row['tree']);build=Path(row['build']);dest=r.OUT/mode
  assert r.sha(tree/'fs/btrfs/super.c')==row['source_after_sha256']
  make=['make','-C',tree,f'O={build}','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-']
  r.run(make+['olddefconfig'],'olddefconfig_'+mode)
  assert r.sha(build/'.config')==row['baseline_build']['config_sha256']
  r.run(make+['-j6','Image'],'build_'+mode,1800)
  r.run(make+['fs/btrfs/super.i'],'preprocess_'+mode)
  shutil.copyfile(build/'fs/btrfs/super.i',dest/'super.i');shutil.copyfile(build/'.config',dest/'kernel.config')
  image=build/'arch/arm64/boot/Image';disk=BASE/(mode+'.img');assert not disk.exists();shutil.copyfile(blank,disk);assert r.sha(disk)==blank_sha
  p=r.run(['btrfs','inspect-internal','dump-super',disk],'super_'+mode);shutil.copyfile(p,dest/'super.txt')
  cmd=['qemu-system-aarch64','-machine','virt','-cpu','max','-m','1024','-smp','1','-nographic','-no-reboot','-kernel',image,'-initrd',initrd,'-append','console=ttyAMA0 rdinit=/init panic=-1','-drive',f'file={disk},format=raw,if=none,id=fs','-device','virtio-blk-device,drive=fs','-nic','none']
  p=r.run(cmd,'boot_'+mode,180);shutil.copyfile(p,dest/'boot.log')
  p=r.run(['btrfs','inspect-internal','dump-tree','-t','5',disk],'tree_'+mode);shutil.copyfile(p,dest/'tree.txt')
  assert 'EXPERIMENT_DONE failures=0' in (dest/'boot.log').read_text()
  row.update(image=str(image),image_sha256=r.sha(image),initrd_sha256=r.sha(initrd),disk=str(disk),disk_before_sha256=blank_sha,disk_after_sha256=r.sha(disk),artifacts={n:r.sha(dest/n) for n in ['boot.log','super.txt','tree.txt','super.i','kernel.config']})
  result.append(row);r.save(r.OUT/'progress.json',result)
 r.save(r.OUT/'manifest.json',result)
if __name__=='__main__':
 if sys.argv[1:] == ['prepare']:prepare()
 elif sys.argv[1:] == ['execute']:execute()
 else:raise ValueError('prepare or execute required')
