"""仅当前 LoongArch 构建上的小范围静态冒烟；不读取候选清单或历史补丁。"""
import gzip
import json
import subprocess
import sys
from pathlib import Path

import hints4
import settings as S

OUT = S.HERE / 'smoke'
OUT.mkdir(exist_ok=True)


def main():
    if S.TARGET != 'loongarch' or S.BOUNDARY_POOL != 'none':
        raise ValueError('冒烟固定 TARGET=loongarch BOUNDARY_POOL=none')
    build = Path(S.builds_for('CUR')[S.TARGET])
    if not (build/'vmlinux').exists():
        (OUT/'result.json').write_text(json.dumps({'status':'skipped_no_vmlinux'}))
        print('SKIP: no vmlinux'); return
    db = OUT/'compile_commands_loongarch.json'
    r=subprocess.run([sys.executable, '/root/repos/linux/scripts/clang-tools/gen_compile_commands.py',
                      '-d',str(build),'-o',str(db)],capture_output=True,text=True)
    (OUT/'database.log').write_text(r.stdout+r.stderr)
    r.check_returncode()
    cc=json.loads(db.read_text())
    kernel=[e for e in cc if '/arch/loongarch/kernel/' in e['file'] and e['file'].endswith('.c')]
    # 固定选当前源码中的普通单元；不根据候选或修复内容挑选。
    chosen=sorted(kernel,key=lambda e:e['file'])[:3]
    chosen += [e for e in cc if e['file'].endswith('/kernel/futex/syscalls.c')]
    if not chosen:
        raise ValueError('现有构建没有可用的编译命令；不重新构建')
    small=OUT/'selected_compile_commands.json'
    small.write_text(json.dumps(chosen,indent=2))
    facts_path=OUT/'facts_loongarch.json.gz'
    r=subprocess.run([sys.executable,str(S.HERE/'extract3.py'),str(small),'/root/repos/linux',
                      str(facts_path),'--jobs','2'],capture_output=True,text=True)
    (OUT/'extract.log').write_text(r.stdout+r.stderr)
    r.check_returncode()
    facts=json.load(gzip.open(facts_path,'rt'))
    vals={a:{} for a in S.ARCHS}
    # 这里只验证通路；空取值明确记为未知，不冒充完成跨架构常量探测。
    h=hints4.run(facts,vals,{'I1','I2','I3','I4'})
    (OUT/'hints_loongarch.json').write_text(json.dumps(h))
    used_outside=set()
    for f in facts['functions'].values():
        if not f['file'].startswith(S.ARCH_PREFIX) and not S.DRV.search(f['file']):
            used_outside.update(f['body'])
    macros=[{'name':n,'file':m['file']} for n,m in facts['macros'].items()
            if n in used_outside and m.get('file') and S.ARCH_MAC_FILE.search(m['file'])]
    funcs=[{'name':f['name'],'file':f['file']} for f in facts['functions'].values()
           if f['name'] in used_outside and f['file'].startswith(S.ARCH_PREFIX)]
    entries=sorted(f['name'] for f in facts['functions'].values() if f['name'].startswith('__do_sys_'))
    arch_macros=[m for m in macros if S.ARCH_PREFIX in m['file']]
    result={'status':'completed', 'compile_commands':len(cc), 'selected':[e['file'] for e in chosen],
            'unit_status':facts['unit_status'],'units':facts['units'], 'functions':len(facts['functions']),
            'syscall_entries':entries, 'syscall_entries_count':len(entries),
            'tree_boundary':h['stats']['tree_boundary'], 'target_macro_examples':arch_macros[:20],
            'target_function_examples':funcs[:20], 'target_macro_count':len(arch_macros),
            'boundary_pool':S.BOUNDARY_POOL,'values_probed':False, 'stats':h['stats']}
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
