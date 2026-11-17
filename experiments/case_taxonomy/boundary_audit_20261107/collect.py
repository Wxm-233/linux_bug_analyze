"""Read existing artifacts and local kernel history; never scan/build the kernel."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'boundary_enum_20261106'
KSRC = Path('/root/repos/linux')
BASE = Path('/root/work/boundary_build')
sys.path.insert(0, str(OLD))
import enumerate as e

def read(p):
    return e.load_json(p)

def write(name, obj):
    (HERE/name).parent.mkdir(parents=True, exist_ok=True)
    (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def run(args, cwd=KSRC):
    p = subprocess.run(args, cwd=cwd, text=True, encoding='utf-8', capture_output=True)
    if p.returncode not in (0, 1) and not (args[0]=='grep' and p.returncode==2):
        raise RuntimeError((args, p.returncode, p.stderr[-2000:]))
    return {'command': args, 'cwd': str(cwd), 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def context(path, numbers, radius=4):
    if not path.is_file():
        return []
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    wanted = set()
    for n in numbers:
        wanted.update(range(max(1,n-radius), min(len(lines), n+radius)+1))
    return [{'line': n, 'text': lines[n-1]} for n in sorted(wanted)]

def prepare():
    manifest = {str(p.relative_to(OLD)): e.sha256(p) for p in sorted(OLD.rglob('*')) if p.is_file()}
    write('evidence/old_manifest.json', manifest)
    hits = read(OLD/'sample_hits.json')['samples']
    original = {r['id']:r for r in read(HERE.parent/'cross_arch_sample_set_20261102/labels_v2_1.json')}
    units = read(OLD/'units_riscv.json.gz')
    by_source = defaultdict(list)
    for u in units:
        by_source[u['source']].append(u)
    entries = e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    inputs = read(OLD/'result_riscv.json')['inputs']
    cache = BASE/'enumeration/riscv'/e.digest(inputs)
    assert cache.is_dir(), cache
    paths = e.Paths(KSRC, BASE/'riscv_defconfig')
    source_files = sorted({f for h in hits if not h['hit'] for f in h['files']})
    compiled = {}
    allsyms = []
    for f in source_files:
        for u in by_source.get(f, []):
            r = read(cache/f"{u['id']:05d}.json.gz")
            syms = [e.symbol_json(e.Symbol.from_row(s)) | {'defined':s[4], 'external':s[5]} for s in r['symbols'] if s[3][0] in source_files]
            allsyms.extend(syms)
            compiled[str(u['id'])] = {'unit':u, 'entry':entries[u['id']].__dict__ | {'args':entries[u['id']].args}, 'symbols':syms}
    # JSON path conversion
    write('evidence/compiled_sources.json', json.loads(json.dumps(compiled, default=str)))
    symbol_by_file = defaultdict(list)
    for s in read(OLD/'symbols_riscv.json'):
        symbol_by_file[s['definition']['file']].append(s)
    point_by_file = defaultdict(list)
    with gzip.open(OLD/'boundary_riscv.jsonl.gz', 'rt') as stream:
        for line in stream:
            r=json.loads(line)
            if r['use']['file'] in source_files: point_by_file[r['use']['file']].append(r)
    calls=[]
    with gzip.open(OLD/'direct_calls_riscv.jsonl.gz', 'rt') as stream:
        for line in stream:
            r=json.loads(line)
            if r['caller']['definition']['file'] in source_files or r['callee']['definition']['file'] in source_files: calls.append(r)
    write('evidence/relevant_boundaries.json', {'symbols':dict(symbol_by_file), 'points':dict(point_by_file), 'calls':calls})
    (HERE/'evidence/patches').mkdir(parents=True, exist_ok=True)
    config=(BASE/'riscv_defconfig/.config').read_text()
    (HERE/'evidence/riscv.config.txt').write_text(config)
    rows=[]
    for h in hits:
        if h['hit']: continue
        ident=h['id']
        p=run(['git','--no-optional-locks','show','--format=fuller','--find-renames','-U3', h['commit']])
        assert p['exit_code']==0, ident
        (HERE/f'evidence/patches/{ident}.patch').write_text(p['stdout'], encoding='utf-8')
        current=[]
        for f in h['files']:
            fp=KSRC/f
            names=[fun.rpartition(':')[2] for fun in h['functions'] if fun.rpartition(':')[0]==f]
            commands=[]
            for name in names:
                commands.append(run(['grep','-n','-w','--',name,f]))
            patchnames=re.findall(r'^\+\s*#\s*define\s+(\w+)', p['stdout'], re.M)
            if not names:
                for name in sorted(set(patchnames)):
                    commands.append(run(['grep','-n','-w','--',name,f]))
            numbers=[int(m.group(1)) for q in commands for m in re.finditer(r'^(\d+):', q['stdout'],re.M)]
            make=[]
            par=fp.parent
            while par!=KSRC and par.is_relative_to(KSRC):
                for mk in ['Makefile','Kconfig']:
                    mf=par/mk
                    if mf.exists():
                        ml=mf.read_text(errors='replace').splitlines()
                        token=fp.stem if par==fp.parent else fp.relative_to(par).parts[0]
                        make.extend({'file':str(mf.relative_to(KSRC)), 'line':i,'text':t} for i,t in enumerate(ml,1) if token in t)
                par=par.parent
            current.append({'file':f,'exists':fp.exists(),'compiled_units':by_source.get(f,[]),
                            'searches':commands,'context':context(fp,numbers),'build_rules':make,
                            'boundary_symbols':symbol_by_file.get(f,[]), 'boundary_use_count':len(point_by_file.get(f,[]))})
        rows.append(h | {'subject':original[ident]['subject'], 'reason':original[ident]['reason'],
                          'patch':f'evidence/patches/{ident}.patch','patch_command':{k:v for k,v in p.items() if k!='stdout'},
                          'patch_hunks':re.findall(r'^@@.*',p['stdout'],re.M),'current':current})
    write('evidence/sample_inputs.json', rows)
    print(json.dumps({'misses':len(rows),'compiled_sources':len(compiled),'cache':str(cache),'old_files':len(manifest)}))

if __name__=='__main__': prepare()
