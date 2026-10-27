"""Reconstruct observations from raw boot logs and offline filesystem trees."""
from pathlib import Path
import re,json,hashlib
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'analysis_out'/'btrfs-mount-resume-20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 rows=[]; artifacts={}
 for mode in ['parent','fix']:
  for page,sector in [(64,65536),(64,4096),(4,4096)]:
   d=OUT/f'{mode}-{page}k'/f'sector{sector}'
   boot=(d/'boot.log').read_text();tree=(d/'tree.txt').read_text();superblock=(d/'super.txt').read_text()
   assert 'EXPERIMENT_DONE failures=0' in boot
   assert f'PAGE_SIZE={page*1024}\n' in boot
   assert not any(x in boot for x in ['Kernel panic','Oops:','WARNING:','BUG:','ERROR step='])
   assert re.search(r'sectorsize\s+'+str(sector)+r'\b',superblock)
   assert re.search(r'nodesize\s+65536\b',superblock)
   requests=re.findall(r'MOUNT request=(\d+) rc=0 errno=0',boot)
   options=re.findall(r'BTRFS info \(device vda\): max_inline at (\d+)',boot)
   mounts=re.findall(r'^/dev/vda /mnt btrfs (.*)$',boot,re.M)
   assert len(mounts)==2
   for line,value in zip(mounts,options):
    shown=re.search(r'max_inline=(\d+)',line)
    if shown:assert shown[1]==value
    else:assert value=='2048'  # historical show_options omits default
   assert requests==['2048','8192'] and len(options)==2
   files=re.findall(r'FILE option=(\d+) size=(\d+) inode=(\d+) blocks=(\d+) readback=1',boot)
   persisted=re.findall(r'PERSISTED option=(\d+) size=(\d+) equal=1',boot)
   assert len(files)==6 and set(persisted)=={(o,s) for o,s,_,_ in files}
   extents={}
   for m in re.finditer(r'item \d+ key \((\d+) EXTENT_DATA (\d+)\)(.*?)(?=\n\s*item \d+ key |\Z)',tree,re.S):
    typ=re.search(r'type (\d+) \((\w+)\)',m[3]);assert typ
    extents.setdefault(m[1],[]).append({'offset':int(m[2]),'type':typ[2],'raw':m[0]})
   rec=[]
   for o,s,ino,blocks in files:
    refs=re.findall(r'key \('+ino+r' INODE_REF \d+\).*?name: ([^\n]+)',tree,re.S)
    assert refs==[f'option{o}_size{s}']
    assert len(extents[ino])==1 and extents[ino][0]['offset']==0
    rec.append({'request':int(o),'size':int(s),'inode':int(ino),'blocks':int(blocks),'extent':extents[ino][0]['type'],'persisted_equal':True,'extent_raw':extents[ino][0]['raw']})
   rows.append({'mode':mode,'page_size':page*1024,'sector_size':sector,'effective_max_inline':dict(zip(requests,map(int,options))),'files':rec,'subpage_warning':'read-write for sector size 4096 with page size 65536 is experimental' in boot})
   for n in ['boot.log','tree.txt','super.txt','result.json']:artifacts[str((d/n).relative_to(OUT))]=sha(d/n)
 for page in [64,4]:
  assert (OUT/f'parent-{page}k/kernel.config').read_bytes()==(OUT/f'fix-{page}k/kernel.config').read_bytes()
  binaries=[]
  for mode in ['parent','fix']:
   d=OUT/f'{mode}-{page}k';build=json.loads((d/'build.json').read_text())
   assert sha(d/'kernel.config')==build['config_sha256']
   assert sha(Path(build['image']))==build['image_sha256']
   assert sha(HERE/'init.c')==build['init_source_sha256']
   binaries.append(build['init_sha256'])
  assert binaries[0]==binaries[1]
 for p in OUT.glob('*k/sector*/result.json'):
  r=json.loads(p.read_text());assert sha(Path(r['disk']))==r['disk_sha256']
 result={'scope':'one previously read development case; uninstrumented historical ARM64 kernels; geometry configurations, not CPU ISA contrast','kernel_builds':4,'qemu_boots':6,'rw_mounts':12,'ro_remounts':12,'file_records':36,'independent_positive':0,'independent_normal':0,'paired_configs_byte_equal':True,'observations':rows,'artifact_sha256':artifacts}
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps([{k:v for k,v in r.items() if k!='files'}|{'layouts':[(f['request'],f['size'],f['extent']) for f in r['files']]} for r in rows],indent=2))
if __name__=='__main__':main()
