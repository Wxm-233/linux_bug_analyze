"""Compile a static PID1 observer and deterministic external gzip newc initrd."""
from pathlib import Path
import gzip
import hashlib
import json
import stat
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=Path('/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out=HERE/'guest_build.json'
    if out.exists():
        raise ValueError('preserve guest build')
    ROOT.mkdir(exist_ok=True)
    binary=ROOT/'init'; initrd=ROOT/'initramfs.cpio.gz'
    if binary.exists() or initrd.exists():
        raise ValueError('preserve existing guest files')
    argv=['aarch64-linux-gnu-gcc','-O2','-static','-Wall','-Wextra','-Werror',str(HERE/'guest.c'),'-o',str(binary)]
    result=subprocess.run(argv,capture_output=True,timeout=60)
    (HERE/'guest_compile.stdout.log').write_bytes(result.stdout); (HERE/'guest_compile.stderr.log').write_bytes(result.stderr)
    if result.returncode:
        out.write_text(json.dumps({'returncode':result.returncode,'argv':argv},indent=2)+'\n')
        raise ValueError('guest_compile_failed')
    data=bytearray(); inode=0
    def entry(name,mode,content=b'',major=0,minor=0):
        nonlocal inode
        inode+=1; encoded=name.encode()+b'\0'
        fields=[inode,mode,0,0,1,0,len(content),0,0,major,minor,len(encoded),0]
        data.extend(('070701'+''.join(f'{v:08x}' for v in fields)).encode()); data.extend(encoded)
        data.extend(b'\0'*((-len(data))%4)); data.extend(content); data.extend(b'\0'*((-len(data))%4))
    for name in ['dev','proc','sys','tmp']:
        entry(name,stat.S_IFDIR|0o755)
    entry('dev/console',stat.S_IFCHR|0o600,major=5,minor=1)
    entry('init',stat.S_IFREG|0o755,binary.read_bytes())
    entry('TRAILER!!!',0)
    initrd.write_bytes(gzip.compress(bytes(data),mtime=0))
    receipt={'returncode':0,'argv':argv,'guest_source_sha256':sha(HERE/'guest.c'),'binary':str(binary),
             'binary_sha256':sha(binary),'initrd':str(initrd),'initrd_sha256':sha(initrd),
             'newc_uncompressed_bytes':len(data),'initrd_bytes':initrd.stat().st_size}
    out.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))

if __name__=='__main__':
    main()
