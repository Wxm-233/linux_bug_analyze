from pathlib import Path
import importlib.util,subprocess as sp,json,shutil
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('runner',HERE.parent/'btrfs_mount_resume_20261023/run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
r.OUT=PROJECT/'analysis_out/btrfs-source-runtime-bridge-20261023'
OLD=PROJECT/'analysis_out/btrfs-mount-resume-20261023'
BASE=Path('/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023')
def main():
 r.OUT.mkdir(parents=True,exist_ok=True);records=[]
 assert not (r.OUT/'manifest.json').exists()
 for mode in ['parent','fix']:
  tree=BASE/mode/'source';source={}
  rev=r.REVS[mode]
  for name in ['fs/btrfs/disk-io.c','fs/btrfs/super.c','fs/btrfs/ctree.h','include/asm-generic/unaligned.h']:
   data=(tree/name).read_bytes();assert data==sp.check_output(['git','-C','/root/repos/linux','show',rev+':'+name])
   d=r.OUT/mode/'source';d.mkdir(parents=True,exist_ok=True);p=d/name.replace('/','__');p.write_bytes(data);source[name]={'path':str(p),'sha256':r.sha(p)}
  for page in [64,4]:
   build=BASE/f'{mode}-{page}k';old=json.loads((OLD/f'{mode}-{page}k/build.json').read_text());image=Path(old['image'])
   assert r.sha(image)==old['image_sha256'] and r.sha(build/'.config')==old['config_sha256']
   dest=r.OUT/f'{mode}-{page}k';dest.mkdir(exist_ok=True);files={}
   for unit in ['disk-io','super']:
    r.run(['make','-C',tree,f'O={build}','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',f'fs/btrfs/{unit}.i'],f'{mode}_{page}_{unit}')
    src=build/f'fs/btrfs/{unit}.i';p=dest/(unit+'.i');shutil.copyfile(src,p)
    cmd=build/f'fs/btrfs/.{unit}.i.cmd';shutil.copyfile(cmd,dest/(unit+'.cmd'))
    files[unit]={'path':str(p),'sha256':r.sha(p),'command_sha256':r.sha(dest/(unit+'.cmd'))}
   assert r.sha(image)==old['image_sha256'] and r.sha(build/'.config')==old['config_sha256']
   records.append({'profile':f'{mode}-{page}k','mode':mode,'page_size':page*1024,'revision':rev,'source_root':str(tree),'sources':source,'preprocessed':files,'build_identity':old,'image_config_unchanged':True})
 r.save(r.OUT/'manifest.json',{'new_preprocess_commands':8,'new_builds':0,'new_boots':0,'profiles':records})
if __name__=='__main__':main()
