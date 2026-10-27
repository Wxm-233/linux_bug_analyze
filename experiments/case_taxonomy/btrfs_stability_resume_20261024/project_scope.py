"""Project existing harness/options facts; never infer path from cache values."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))
source=ROOT/'linux_bug_analyze/experiments/case_taxonomy/btrfs_mount_resume_20261023/init.c'
content=source.read_bytes();text=content.decode('utf-8')
sha=hashlib.sha256(content).hexdigest()
assert all(row['baseline_build']['init_source_sha256']==sha for row in manifest)
assert 'int opts[]={2048,8192};' in text
assert 'snprintf(option,sizeof option,"max_inline=%d",opts[o])' in text
assert 'mount("/dev/vda","/mnt","btrfs",0,option)' in text
assert 'sync();check(!umount("/mnt"),"umount");' in text
assert 'check(!umount("/mnt"),"umount_ro");' in text
facts=[]
for row in manifest:
    folder=raw/row['mode']
    for name in ('boot.log','super.txt'):
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==row['artifacts'][name]
    boot=(folder/'boot.log').read_text(encoding='utf-8')
    disk=(folder/'super.txt').read_text(encoding='utf-8')
    assert re.findall(r'^MOUNT request=(\d+) rc=0 errno=0$',boot,re.M)==['2048','8192']
    assert 'EXPERIMENT_DONE failures=0' in boot and 'ERROR step=' not in boot
    devices=int(re.search(r'^num_devices\s+(\d+)',disk,re.M)[1])
    assert devices==1
    facts.append(dict(mode=row['mode'],revision=row['revision'],disk_num_devices=devices,
        supplied_mount_options=['max_inline=2048','max_inline=8192'],supplied_flags=0,
        preceding_user_options=[],harness_unmount_checks='no errors, final failures=0',
        basis='archived harness source SHA + prior initrd binding + boot results + offline superblock',
        does_not_prove=['internal VFS path','all possible writers','post-LSM argument bytes','parse preamble side effects'],
        path_inferred_from_cache=False))
output=dict(source=str(source),source_sha256=sha,facts=facts,
    admission='These scope facts do not discharge stability premises; deadline remains insufficient.')
(HERE/'scope_facts.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('2 archived boots: single-device metadata; two max_inline-only mount options each; no cache-based path inference')
