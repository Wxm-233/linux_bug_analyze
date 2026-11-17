"""固定输入的 RISC-V 回归；只写本目录，不执行旧程序的输出 main。"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAX = HERE.parents[1]
OUT = HERE / 'regression'
OUT.mkdir(exist_ok=True)
RESULTS = OUT / 'results.json'


def load(path):
    if str(path).endswith('.gz'):
        return json.load(gzip.open(path, 'rt'))
    return json.loads(Path(path).read_text())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def diff(a, b, path='$'):
    if type(a) != type(b):
        return [path + ': type']
    if isinstance(a, dict):
        out = [path + ': keys'] if a.keys() != b.keys() else []
        for k in a.keys() & b.keys():
            out += diff(a[k], b[k], path + '.' + str(k))
            if len(out) > 20:
                break
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + f': length {len(a)} != {len(b)}']
        out=[]
        for i,(x,y) in enumerate(zip(a,b)):
            out += diff(x,y,path+f'[{i}]')
            if len(out)>20: break
        return out
    return [] if a==b else [path+f': {str(a)[:120]} != {str(b)[:120]}']


results = load(RESULTS) if RESULTS.exists() else {}


def record(name, a, b, extra=None):
    ds = diff(a,b)
    results[name] = {'equal': not ds, 'differences': ds, **(extra or {})}
    # 每项比较独立保存，避免并行阶段互相覆盖汇总文件。
    (OUT / (name + '.comparison.json')).write_text(json.dumps(results[name], ensure_ascii=False, indent=2))
    print(name, 'PASS' if not ds else 'DIFF', ds[:3], flush=True)


def cmd(args, name):
    r = subprocess.run([sys.executable, *map(str,args)], text=True, capture_output=True)
    (OUT / (name + '.log')).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError(f'{name} rc={r.returncode}: {r.stderr[-1500:]}')
    print(name, r.stdout.strip()[-500:], flush=True)


def hints():
    import hints4
    facts=load('/root/work/casemodel/facts/CUR.json.gz')
    vals=load('/root/work/static2/values/CUR.json')
    cfg={'I1','I2','I3','I4'}
    h=hints4.run(facts,vals,cfg)
    old=module('legacy_hints4', TAX/'casemodel_dev_20261110/static/hints4.py').run(facts,vals,cfg)
    record('hints_vocab_saved', h['vocab'], load(TAX/'casemodel_dev_20261110/gen/vocab_CUR.json')['vocab'],
           {'syscalls':len(h['vocab'])})
    record('hints_stats', h['stats'],old['stats'], {'stats':h['stats']})
    record('hints_sites', h['sites'],old['sites'], {'sites_count':sum(map(len,h['sites'].values()))})
    record('hints_all', h,old)
    stfacts=load('/root/work/static2/facts/CUR.json.gz')
    st=hints4.run(stfacts,vals,cfg)
    record('fact_versions_sites', h['sites'],st['sites'],
           {'casemodel_sites':h['stats']['sites'], 'static2_sites':st['stats']['sites'],
            'fact_fields_differ': sorted(set(facts['functions']) ^ set(stfacts['functions'])),
            'note':'此项为事实版本诊断，不是新旧实现回归；rank 使用 static2 事实'})
    legacy3=module('legacy_hints3', TAX/'rankprune_dev_20261110/static/hints3.py').run(stfacts,vals,cfg)
    record('rank_sites_legacy3',st['sites'],legacy3['sites'])


def rank():
    out=OUT/'rank'; out.mkdir(exist_ok=True)
    cmd([HERE/'rank.py','CUR','--facts','/root/work/static2/facts/CUR.json.gz','--values',
         '/root/work/static2/values/CUR.json','--out-dir',out], 'rank')
    record('rank_hints_saved',load(out/'hints_CUR.json'),load(TAX/'rankprune_dev_20261110/gen/hints_CUR.json'))
    record('rank_ranking_saved',load(out/'ranking_CUR.json'),load(TAX/'rankprune_dev_20261110/ranking_CUR.json'))


def layouts():
    out=OUT/'layouts_CUR.json'
    cmd([HERE/'layouts.py','CUR','/root/work/casemodel/facts/CUR.json.gz','--out',out], 'layouts')
    data=load(out)
    record('layouts_saved',data,load(TAX/'casemodel_dev_20261110/gen/layouts_CUR.json'),
           {'roots':len(data['roots']), 'types':{a:len(data[a]) for a in ('riscv','arm64','x86_64')},
            'errors':{a:data[a+'_errors'] for a in ('riscv','arm64','x86_64')}})


def extract():
    base=['/root/work/boundary_build/riscv_defconfig/compile_commands.json','/root/repos/linux']
    for label,script in [('old',TAX/'casemodel_dev_20261110/static/extract3.py'),('new',HERE/'extract3.py')]:
        cmd([script,*base,OUT/f'extract_{label}.json.gz','--jobs','1','--only',r'kernel/futex/syscalls\.c$'], 'extract_'+label)
    old,new=[load(OUT/f'extract_{l}.json.gz') for l in ('old','new')]
    for d in (old,new):
        d.pop('seconds',None)
        for u in d['units']: u.pop('seconds',None)
    assert new['unit_status'].get('base:ok') == 1, new['unit_status']
    record('extract_futex',new,old,{'unit_status':new['unit_status'],'functions':len(new['functions']),
                                 'macros':len(new['macros']), 'ignored_fields':['seconds','units[*].seconds']})


def audit():
    manifest=load(HERE/'source_manifest.json')
    changed=[f for f,h in manifest.items() if hashlib.sha256((TAX/f).read_bytes()).hexdigest()!=h]
    record('old_files_unchanged',changed,[])
    out = OUT / 'rank'
    record('rank_hints_saved',load(out/'hints_CUR.json'),load(TAX/'rankprune_dev_20261110/gen/hints_CUR.json'))
    record('rank_ranking_saved',load(out/'ranking_CUR.json'),load(TAX/'rankprune_dev_20261110/ranking_CUR.json'))
    data=load(OUT/'layouts_CUR.json')
    record('layouts_saved',data,load(TAX/'casemodel_dev_20261110/gen/layouts_CUR.json'),
           {'roots':len(data['roots']), 'types':{a:len(data[a]) for a in ('riscv','arm64','x86_64')},
            'errors':{a:data[a+'_errors'] for a in ('riscv','arm64','x86_64')}})
    # 旧汇总仅剩抽取结果；迁入独立文件，无需重新执行已经完成的抽取。
    if 'extract_futex' in results and not (OUT/'extract_futex.comparison.json').exists():
        (OUT/'extract_futex.comparison.json').write_text(json.dumps(results['extract_futex'],indent=2))
    combined={p.name.removesuffix('.comparison.json'):load(p) for p in sorted(OUT.glob('*.comparison.json'))}
    RESULTS.write_text(json.dumps(combined,ensure_ascii=False,indent=2))
    assert all(x['equal'] for k,x in combined.items() if k!='fact_versions_sites'), combined


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('phase', choices=['hints','rank','layouts','extract','audit'])
    args=ap.parse_args()
    if os.environ.get('TARGET','riscv')!='riscv': raise ValueError('回归固定 TARGET=riscv')
    globals()[args.phase]()
