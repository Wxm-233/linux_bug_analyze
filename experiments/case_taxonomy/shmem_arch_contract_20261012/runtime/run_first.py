"""First bounded shmem historical ARM64/64K kernel run; no synthetic folios."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANT = 'old'
TAG = 'old64k'
PROFILE = 'old_arm64_64k'
CONFIG_BASE = None
PATCH_FILE = HERE / 'observation.patch'
REV = '3390916aca7af1893ed2ebcdfee1d6fdb65bb058'
BASE = Path('/root/.cache/linux-bug-analyze/shmem-contract-20261012/runtime')
TREE = BASE / 'old/linux'
BUILD = BASE / 'old_arm64_64k/build'
OUT = HERE / 'old_arm64_64k'
ENV = dict(os.environ, LC_ALL='C', LANG='C')


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, label, timeout=900):
    records = json.loads((OUT/'commands.json').read_text()) if (OUT/'commands.json').exists() else []
    number = 1 + sum(r['label'] == label for r in records)
    stem = label if number == 1 else f'{label}.attempt{number}'
    row = dict(label=label, attempt=number, argv=argv,
               stdout=str(OUT/(stem+'.stdout.log')), stderr=str(OUT/(stem+'.stderr.log')), status='running')
    records.append(row); save(OUT/'commands.json', records)
    save(OUT/'progress.json', {'step':label,'attempt':number,'state':'running'})
    print(label, flush=True)
    start = time.monotonic()
    with open(row['stdout'],'wb') as out, open(row['stderr'],'wb') as err:
        try:
            rc = subprocess.run(argv,stdout=out,stderr=err,env=ENV,timeout=timeout).returncode
        except subprocess.TimeoutExpired: rc = 124
    row.update(exit_code=rc,seconds=round(time.monotonic()-start,2),status='finished')
    save(OUT/'commands.json', records); save(OUT/'progress.json', row)
    if rc:
        raise RuntimeError(f'{label} exit {rc}: {Path(row["stderr"]).read_text(errors="replace")[-1800:]}')
    return row


def config(path):
    result={}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            k,v=line.split('=',1); result[k]=v
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            result[line[2:-11]]='n'
    return result


def prepare(refresh_kernel=False):
    marker = BASE/VARIANT/'source_revision'
    if not marker.exists():
        TREE.mkdir(parents=True,exist_ok=True)
        print('archive fixed parent revision into independent cache',flush=True)
        archive=subprocess.Popen(['git','-C','/root/repos/linux','archive',REV],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        extracted=subprocess.run(['tar','-xf','-','-C',str(TREE)],stdin=archive.stdout,capture_output=True)
        archive.stdout.close(); err=archive.stderr.read(); rc=archive.wait()
        if rc or extracted.returncode: raise RuntimeError(f'archive/tar failed: {err!r} {extracted.stderr!r}')
        marker.write_text(REV+'\n')
    if marker.read_text().strip()!=REV: raise RuntimeError('Source cache has another revision')
    paths=sorted({r['path'] for r in json.loads((HERE.parent/'source_chain.json').read_text())['sources']} | {'Makefile'})
    entries=subprocess.check_output(['git','-C','/root/repos/linux','ls-tree','-r',REV,'--']+paths).decode().splitlines()
    identities=[]
    instrumentation_file=BASE/VARIANT/'observation.json'
    instrumentation=json.loads(instrumentation_file.read_text()) if instrumentation_file.exists() else None
    for entry in entries:
        meta,path=entry.split('\t'); blob=meta.split()[2]; data=(TREE/path).read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual!=blob:
            if path!='mm/shmem.c' or not instrumentation or sha(TREE/path)!=instrumentation['observed_sha256']:
                raise RuntimeError(f'Historical source changed unexpectedly: {path}')
            original=(BASE/VARIANT/'shmem.c.original').read_bytes()
            if hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest()!=blob:
                raise RuntimeError('Observation patch base has another revision')
        identities.append(dict(path=path,git_blob=blob,actual_matches_git=actual==blob,
                               observation_patch_verified=actual!=blob and bool(instrumentation)))
    save(OUT/'source_identity.json',identities)
    make=['make','-C',str(TREE),f'O={BUILD}','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','WERROR=0']
    if not (BUILD/'arch/arm64/boot/Image').exists():
        if CONFIG_BASE:
            BUILD.mkdir(parents=True,exist_ok=True)
            (BUILD/'.config').write_bytes(CONFIG_BASE.read_bytes())
        else:
            run(make+['allnoconfig'],'allnoconfig')
        edits=[str(TREE/'scripts/config'),'--file',str(BUILD/'.config')]
        enabled=['ARM64_64K_PAGES','ARM64_VA_BITS_48','ARCH_VIRT','ARM_GIC_V3',
                 'SERIAL_AMBA_PL011','SERIAL_AMBA_PL011_CONSOLE','ARM_ARCH_TIMER',
                 'BLK_DEV_INITRD','RD_GZIP','BINFMT_ELF','PRINTK','TTY','DEVTMPFS',
                 'PROC_FS','SYSFS','DEBUG_FS','SHMEM','TMPFS','TRANSPARENT_HUGEPAGE',
                 'COMPACTION','MIGRATION','FTRACE','KPROBES','KPROBE_EVENTS',
                 'KALLSYMS','KALLSYMS_ALL','FUTEX','MULTIUSER','POSIX_TIMERS']
        for k in enabled: edits+=['--enable',k]
        for k in ['ARM64_4K_PAGES','ARM64_16K_PAGES','ARM64_VA_BITS_39','ARM64_VA_BITS_42',
                  'ARM64_VA_BITS_47','ARM64_VA_BITS_52','WERROR','MODULES','BASE_SMALL',
                  'PREEMPT_RT','DEBUG_INFO','LOCALVERSION_AUTO']:
            edits+=['--disable',k]
        edits+=['--set-val','NR_CPUS','4','--set-str','LOCALVERSION',f'-shmem-r3-{TAG}']
        run(edits,'config_edits'); run(make+['olddefconfig'],'olddefconfig')
    if instrumentation:
        # This revision provides trace_printk through CONFIG_TRACING, not a
        # standalone CONFIG_TRACE_PRINTK symbol.
        run([str(TREE/'scripts/config'),'--file',str(BUILD/'.config'),
             '--set-str','LOCALVERSION',f'-shmem-r3-{TAG}-obs1'],'observation_config')
        run(make+['olddefconfig'],'observation_olddefconfig')
    actual=config(BUILD/'.config')
    required=['ARM64_64K_PAGES','SHMEM','TMPFS','TRANSPARENT_HUGEPAGE','XARRAY_MULTI',
              'COMPACTION','MIGRATION','KPROBES','KRETPROBES','KPROBE_EVENTS','TRACING',
              'BINFMT_ELF','BLK_DEV_INITRD','RD_GZIP','PROC_FS','SYSFS',
              'SERIAL_AMBA_PL011_CONSOLE','DEVTMPFS']
    missing=[k for k in required if actual.get('CONFIG_'+k)!='y']
    if missing or actual.get('CONFIG_ARM64_VA_BITS')!='48':
        raise RuntimeError(f'Unreachable configuration: {missing}')
    if CONFIG_BASE:
        baseline=config(CONFIG_BASE)
        differences=[k for k in set(actual)|set(baseline)
                     if k!='CONFIG_LOCALVERSION' and actual.get(k)!=baseline.get(k)]
        save(OUT/'config_pair.json',{'baseline':str(CONFIG_BASE),'ignored_label':'CONFIG_LOCALVERSION',
                                   'differences':differences})
        if differences: raise RuntimeError(f'Paired configuration changed: {differences}')
    (OUT/'kernel.config').write_bytes((BUILD/'.config').read_bytes())
    if refresh_kernel or not (BUILD/'arch/arm64/boot/Image').exists():
        run(make+['-j6','Image'],'kernel_build')
    image=BUILD/'arch/arm64/boot/Image'
    run(['aarch64-linux-gnu-readelf','-h',str(BUILD/'vmlinux')],'kernel_elf')
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(BUILD/'vmlinux')]).decode().splitlines()
    targets=['truncate_inode_partial_folio','split_huge_page_to_list_to_order','xas_split_alloc','shmem_fallocate']
    if not instrumentation: targets+=['alloc_pages_mpol','shmem_add_to_page_cache']
    named={line.split()[-1] for line in symbols if line.split()}
    availability={n:n in named for n in targets}
    save(OUT/'probe_symbols.json',availability)
    if not all(availability.values()):
        raise RuntimeError('Required exact probe symbols absent; do not guess optimized function ABI')
    includes=[TREE/'arch/arm64/include',BUILD/'arch/arm64/include/generated',TREE/'include',BUILD/'include',
              TREE/'arch/arm64/include/uapi',BUILD/'arch/arm64/include/generated/uapi',TREE/'include/uapi',BUILD/'include/generated/uapi']
    args=['aarch64-linux-gnu-gcc','-O2','-D__KERNEL__','-fno-stack-protector',
          '-include',str(TREE/'include/linux/kconfig.h'),'-include',str(TREE/'include/linux/compiler_types.h')]
    for path in includes: args+=['-I',str(path)]
    run(args+[str(HERE/'layout.c'),'-o',str(BUILD/'layout')],'layout_build')
    receipt=run(['qemu-aarch64','-L','/usr/aarch64-linux-gnu',str(BUILD/'layout')],'layout_read')
    geometry=json.loads(Path(receipt['stdout']).read_text())
    if (geometry['PAGE_SHIFT'],geometry['PMD_SHIFT'],geometry['HPAGE_PMD_ORDER'],geometry['XA_CHUNK_SHIFT'])!=(16,29,13,6) or geometry['MAX_PAGE_ORDER']<13 or geometry['ULONG_BYTES']!=8:
        raise RuntimeError(f'Unexpected actual geometry: {geometry}')
    save(OUT/'layout.json',geometry)
    (BUILD/'layout.h').write_text('\n'.join(f'#define {k} {v}UL' for k,v in geometry.items())+'\n')
    run(['aarch64-linux-gnu-gcc','-static','-Os','-std=c11','-Wall','-Wextra','-fno-pie','-no-pie',
         '-I',str(BUILD),str(HERE/'init_shmem.c'),'-o',str(BUILD/'pid1.elf')],'init_build')
    receipt=run(['aarch64-linux-gnu-readelf','-h','-l',str(BUILD/'pid1.elf')],'init_elf')
    elf=Path(receipt['stdout']).read_text()
    if 'INTERP' in elf or not re.search(r'Class:\s+ELF64',elf) or not re.search(r'Machine:\s+AArch64',elf): raise RuntimeError('Wrong init identity')
    listing=BUILD/'initramfs.list'
    listing.write_text('dir /dev 755 0 0\ndir /proc 755 0 0\ndir /sys 755 0 0\ndir /trace 755 0 0\ndir /work 755 0 0\n'
                       'nod /dev/console 600 0 0 c 5 1\n'+f'file /init {BUILD/"pid1.elf"} 755 0 0\n')
    raw=subprocess.check_output([str(BUILD/'usr/gen_init_cpio'),str(listing)])
    initrd=BUILD/'initramfs.cpio.gz';initrd.write_bytes(gzip.compress(raw,mtime=0))
    row=dict(status='READY',revision=REV,profile=PROFILE,image=str(image),initrd=str(initrd),
             release=(BUILD/'include/config/kernel.release').read_text().strip(),geometry=geometry,
             source_instrumentation=bool(instrumentation),instrumentation=instrumentation,
             source_identity=identities,config_sha256=sha(BUILD/'.config'),
             init_source_sha256=sha(HERE/'init_shmem.c'),layout_source_sha256=sha(HERE/'layout.c'),
             image_sha256=sha(image),initrd_sha256=sha(initrd),init_binary_sha256=sha(BUILD/'pid1.elf'))
    save(OUT/'build.json',row); return row


def ready_build():
    """Use the reviewed build once, refusing stale inputs or artifacts."""
    build=json.loads((OUT/'build.json').read_text())
    if build['status']!='READY' or build['revision']!=REV:
        raise RuntimeError('No ready build at the fixed revision')
    for path,key in [(BUILD/'.config','config_sha256'),
                     (HERE/'init_shmem.c','init_source_sha256'),
                     (HERE/'layout.c','layout_source_sha256'),
                     (Path(build['image']),'image_sha256'),
                     (Path(build['initrd']),'initrd_sha256'),
                     (BUILD/'pid1.elf','init_binary_sha256')]:
        if sha(path)!=build[key]: raise RuntimeError(f'Ready build changed: {path.name}')
    if config(BUILD/'.config').get('CONFIG_TRACING')!='y':
        raise RuntimeError('Historical trace_printk requires CONFIG_TRACING=y')
    if sha(TREE/'mm/shmem.c')!=build['instrumentation']['observed_sha256']:
        raise RuntimeError('Observed source changed')
    if sha(PATCH_FILE)!=build['instrumentation']['patch_sha256']:
        raise RuntimeError('Observation patch changed')
    elf=subprocess.check_output(['aarch64-linux-gnu-readelf','-h',str(BUILD/'vmlinux')]).decode()
    if not re.search(r'Class:\s+ELF64',elf) or not re.search(r'Machine:\s+AArch64',elf):
        raise RuntimeError('Wrong kernel ELF identity')
    return build


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--build-only',action='store_true')
    ap.add_argument('--boot-only',action='store_true')
    ap.add_argument('--refresh-kernel',action='store_true');args=ap.parse_args()
    if os.name!='posix':raise RuntimeError('Run within WSL')
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        if args.boot_only and (args.build_only or args.refresh_kernel):
            raise RuntimeError('boot-only cannot request another build')
        build=ready_build() if args.boot_only else prepare(args.refresh_kernel)
        if args.build_only:return
        argv=['qemu-system-aarch64','-accel','tcg','-machine','virt-8.2,gic-version=3','-cpu','max',
              '-smp','1','-m','4096','-nographic','-monitor','none','-no-reboot','-nic','none',
              '-kernel',build['image'],'-initrd',build['initrd'],'-append',
              f'console=ttyAMA0 rdinit=/init panic=1 panic_on_warn=0 loglevel=4 shmem_case={PROFILE}']
        receipt=run(argv,'qemu_boot',timeout=300)
        save(OUT/'boot_receipt.json',dict(build=build,qemu=receipt,status='OBSERVED_UNREVIEWED'))
    except Exception as error:
        save(OUT/'error.json',{'status':'INCOMPLETE','reason':str(error)})
        print(str(error),flush=True);raise SystemExit(1)


if __name__=='__main__':main()
