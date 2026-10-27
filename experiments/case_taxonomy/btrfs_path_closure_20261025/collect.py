"""Copy fixed revision source bytes and bounded lexical anchors, no semantic verdict."""
from pathlib import Path
import subprocess,json,hashlib,re
HERE=Path(__file__).resolve().parent
REV='0d977e0eba234e01a60bdde27314dc21374201b3'
FILES=['fs/btrfs/super.c','fs/btrfs/ctree.h','fs/btrfs/free-space-cache.c','fs/btrfs/zoned.h',
       'fs/super.c','fs/fs_context.c','fs/namespace.c','include/asm-generic/unaligned.h',
       'lib/string.c','lib/parser.c','lib/cmdline.c']
PATTERN=r'get_unaligned_le32|__get_unaligned_t|btrfs_free_space_cache_v1_active|btrfs_is_zoned|legacy_get_tree|fc_mount\(|vfs_kern_mount\(|btrfs_mount\(|btrfs_mount_root\(|btrfs_root_fs_type|btrfs_fs_compat_ro|btrfs_set_opt|btrfs_set_and_info|btrfs_clear_and_info|btrfs_clear_opt|strsep\(|match_token\(|match_strdup\(|memparse\(|iterate_supers\(|get_active_super\(|user_get_super\('
rows=[]
folder=HERE/'source';folder.mkdir(exist_ok=False)
for path in FILES:
    raw=subprocess.check_output(['git','-C','/root/repos/linux','show',REV+':'+path])
    target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    lines=raw.decode().splitlines()
    rows.append(dict(path=path,revision=REV,sha256=hashlib.sha256(raw).hexdigest(),lines=len(lines),
                     hits=[dict(line=n,text=s) for n,s in enumerate(lines,1) if re.search(PATTERN,s)]))
(HERE/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps([dict(path=r['path'],hits=[h['line'] for h in r['hits']]) for r in rows]))
