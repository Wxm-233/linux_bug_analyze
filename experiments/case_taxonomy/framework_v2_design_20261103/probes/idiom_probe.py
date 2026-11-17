"""Post-hoc probe (no model): for each C positive, does the RISC-V fix add identifiers that the labelled counterpart
already had while the fixed RISC-V file did not (at fix^)? And how could the counterpart file be paired by path?"""
import json, re, subprocess, sys
from collections import Counter

REPO = '/root/repos/linux'
BASE = sys.argv[1]
KW = set('if else for while do return switch case break continue goto sizeof struct union enum static const '
         'void int long short char unsigned signed bool true false NULL inline extern volatile default typeof u8 u16 '
         'u32 u64 s8 s16 s32 s64 define include ifdef ifndef endif elif undef err ret val ptr addr size i j k'.split())
ID = re.compile(r'[A-Za-z_]\w{2,}')
PATH = re.compile(r'((?:arch|include|kernel|mm|drivers|lib|init|scripts|sound|net|fs)/[\w./-]+\.(?:c|h|S)|'
                  r'(?:arch|scripts)/[\w./-]*Makefile[\w.]*|init/Kconfig)')


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def ids(lines):
    return {x for l in lines for x in ID.findall(re.sub(r'/\*.*?\*/|//.*', '', l))} - KW


def rel(p):
    m = re.match(r'arch/[^/]+/(.*)', p)
    return m.group(1) if m else None


labels = json.load(open(f'{BASE}/cross_arch_sample_set_20261102/labels_v2_1.json', encoding='utf-8'))
pos = [r for r in labels if r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误')]
rows = []
for r in pos:
    sha = r['commit']
    diff = git('show', '--format=', '-U0', sha)
    plus = [l[1:] for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++')]
    minus = [l[1:] for l in diff.splitlines() if l.startswith('-') and not l.startswith('---')]
    added = ids(plus) - ids(minus)
    cps = sorted(set(PATH.findall(r['counterpart'])))
    cp_text = ''.join(git('show', f'{sha}^:{p}') for p in cps)
    fixed_text = ''.join(git('show', f'{sha}^:{p}') for p in r['files'])
    cp_ids = set(ID.findall(cp_text))
    fx_ids = set(ID.findall(fixed_text))
    transfer = sorted(x for x in added if x in cp_ids and x not in fx_ids)
    # path pairing of the counterpart to a fixed RISC-V file
    pair = 'none'
    for p in cps:
        for f in r['files']:
            if not f.startswith('arch/riscv'):
                continue
            if rel(p) and rel(p) == rel(f):
                pair = 'same_subpath'
            elif pair not in ('same_subpath',) and rel(p) and rel(f) and rel(p).split('/')[0] == rel(f).split('/')[0] \
                    and p.rsplit('/', 1)[-1].split('.')[0][:4] == f.rsplit('/', 1)[-1].split('.')[0][:4]:
                pair = 'same_dir_similar_name'
            elif pair == 'none' and rel(p) and rel(f) and rel(p).split('/')[0] == rel(f).split('/')[0]:
                pair = 'same_top_dir'
        if not p.startswith('arch/') and pair == 'none':
            pair = 'common'
    rows.append({'id': r['id'], 'dev': r['dev'], 'after_snap': r['date'] > '2024-11-17', 'mech': r['mechanism'],
                 'kind': r['counterpart_kind'], 'counterparts': cps, 'transfer': transfer[:8], 'pair': pair})
json.dump(rows, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for grp, sel in (('test_after', lambda x: not x['dev'] and x['after_snap']), ('dev', lambda x: x['dev'])):
    xs = [x for x in rows if sel(x)]
    print(grp, len(xs), 'transfer', sum(bool(x['transfer']) for x in xs),
          Counter(x['pair'] for x in xs), Counter((x['kind'], bool(x['transfer'])) for x in xs))
