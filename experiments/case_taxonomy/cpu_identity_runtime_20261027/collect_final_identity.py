"""Freeze actual instrumented sources, configuration delta and build identity."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE=Path(__file__).resolve().parent

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def config(path):
    values={}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key,value=line.split('=',1); values[key]=value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line.split()[1]]='n'
    return values

def main():
    target=HERE/'final_source_identity.json'
    if target.exists(): raise ValueError('preserve final identity')
    build=json.loads((HERE/'build_complete.json').read_bytes()); root=Path(build['source_root'])
    rows=json.loads((HERE/'source_manifest.json').read_bytes())
    patches=json.loads((HERE/'instrumentation.json').read_bytes())
    modified={row['path']:row for row in patches['files']}
    for row in rows:
        actual=sha(root/row['path'])
        expected=modified[row['path']]['after_sha256'] if row['path'] in modified else row['sha256']
        if actual!=expected: raise ValueError('source changed after build:'+row['path'])
    for name in modified:
        path=HERE/'observed_sources'/name; path.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(root/name,path)
    before=config(HERE/'baseline.config'); after=config(HERE/'kernel.config')
    changes={key:{'before':before.get(key),'after':after.get(key)} for key in sorted(set(before)|set(after)) if before.get(key)!=after.get(key)}
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm','-S',build['vmlinux']],text=True)
    selected=[line for line in symbols.splitlines() if line.split()[-1] in ['nr_cpu_ids','setup_max_cpus','__cpu_logical_map']]
    result={'status':'verified','revision':build['revision'],'source_files_checked':len(rows),'instrumented_source_files':list(modified),
        'configuration_changes_from_existing_baseline':changes,'state_symbols':selected,
        'Image_sha256':sha(Path(build['image'])),'vmlinux_sha256':sha(Path(build['vmlinux'])),
        'config_sha256':sha(Path(build['build_directory'])/'.config'),'new_kernel_builds':1,'new_PID1_builds':1,
        'former_virtio_cache_modified':False}
    if result['Image_sha256']!=build['image_sha256'] or result['vmlinux_sha256']!=build['vmlinux_sha256'] or result['config_sha256']!=build['config_sha256']:
        raise ValueError('kernel identity changed during runs')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
