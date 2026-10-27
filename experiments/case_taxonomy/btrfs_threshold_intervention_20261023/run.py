"""Two crossed-order runs from identical disk clones, one existing kernel."""
from pathlib import Path
import importlib.util,json,shutil,gzip,subprocess as sp
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'btrfs_mount_resume_20261023'
spec=importlib.util.spec_from_file_location('prior_runner',OLD/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
r.OUT=HERE.parents[2]/'analysis_out'/'btrfs-threshold-intervention-20261023'
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-threshold-intervention-20261023')
def main():
 assert not (r.OUT/'manifest.json').exists(),'preserve completed run'
 r.OUT.mkdir(parents=True,exist_ok=True);BASE.mkdir(parents=True,exist_ok=True)
 oldout=HERE.parents[2]/'analysis_out'/'btrfs-mount-resume-20261023'
 build=json.loads((oldout/'fix-64k/build.json').read_text());image=Path(build['image'])
 config=oldout/'fix-64k/kernel.config'
 assert r.sha(image)==build['image_sha256'] and r.sha(config)==build['config_sha256']
 shutil.copyfile(config,r.OUT/'kernel.config')
 r.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra',HERE/'init.c','-o',BASE/'pid1.elf'],'init_build')
 listing=BASE/'initramfs.list';listing.write_text('dir /dev 755 0 0\nnod /dev/console 600 0 0 c 5 1\n'+f'file /init {BASE}/pid1.elf 755 0 0\n')
 initrd=BASE/'initrd.gz';generator=image.parents[3]/'usr/gen_init_cpio'
 initrd.write_bytes(gzip.compress(sp.check_output([str(generator),str(listing)]),mtime=0))
 blank=BASE/'blank.img'
 with blank.open('xb') as f:f.truncate(512*1024*1024)
 r.run(['mkfs.btrfs','-f','-s','65536','-n','65536','-m','single','-d','single','-O','^free-space-tree',blank],'mkfs')
 blankhash=r.sha(blank)
 manifest={'revision':build['revision'],'image':str(image),'image_sha256':r.sha(image),'config_sha256':r.sha(config),'initrd_sha256':r.sha(initrd),'init_source_sha256':r.sha(HERE/'init.c'),'baseline_sha256':blankhash,'runs':[]}
 for order in ['AB','BA']:
  d=r.OUT/order;d.mkdir();disk=BASE/(order+'.img');assert not disk.exists();shutil.copyfile(blank,disk);assert r.sha(disk)==blankhash
  p=r.run(['btrfs','inspect-internal','dump-super',disk],'super_'+order);shutil.copyfile(p,d/'super.txt')
  cmd=['qemu-system-aarch64','-machine','virt','-cpu','max','-m','1024','-smp','1','-nographic','-no-reboot','-kernel',image,'-initrd',initrd,'-append',f'console=ttyAMA0 rdinit=/init panic=-1 order={order}','-drive',f'file={disk},format=raw,if=none,id=fs','-device','virtio-blk-device,drive=fs','-nic','none']
  p=r.run(cmd,'boot_'+order,180);shutil.copyfile(p,d/'boot.log')
  p=r.run(['btrfs','inspect-internal','dump-tree','-t','5',disk],'tree_'+order);shutil.copyfile(p,d/'tree.txt')
  assert 'EXPERIMENT_DONE failures=0' in (d/'boot.log').read_text()
  manifest['runs'].append({'order':order,'disk':str(disk),'before_sha256':blankhash,'after_sha256':r.sha(disk),'artifacts':{n:r.sha(d/n) for n in ['super.txt','boot.log','tree.txt']}})
  r.save(r.OUT/'progress.json',manifest)
 assert r.sha(blank)==blankhash
 r.save(r.OUT/'manifest.json',manifest)
if __name__=='__main__':main()
