"""Migration prompts (criteria.md section 2) for one split of replay_samples_more_20261105/labels_all.json.

    python3 -B build_prompts.py dev|test

For each pair: the reference commits' subjects, messages (trailers removed) and the replay material's
reference.diff; candidate target files chosen only from the reference (section 2: path mapping, then files of
arch/<target>/ at T^ naming the reference's changed functions, macros and Kconfig symbols, at most 5, files over 1500
lines cut to the head, the matching functions and the same-file functions those call directly, at most 12) and the names in those files' directories. Condition S adds
strategy_table.md verbatim; S and N are otherwise identical (checked). Refuses to run unless labels_all.json
matches its recorded SHA. WSL (git); no model calls.
Output: <CALLS>/M_<id>_<S|N>/prompt.md, candidates_<split>.json, prompt_index_<split>.json.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent / 'replay_samples_more_20261105'
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions)

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'replay_migration_20261105'
STRATEGY = (HERE.parent / 'fix_strategy_test_20261105' / 'strategy_table.md').read_text(encoding='utf-8')
TRAILER = re.compile(r'^(Signed-off-by|Cc|Link|Reviewed-by|Tested-by|Acked-by|Reported-by|Closes|Message-ID|'
                     r'Suggested-by|Co-developed-by|Reported-and-tested-by|Fixes|Assisted-by)\s*:', re.I)
MAX_FILES, MAX_LINES, MAX_HEAD, COMMON_LIMIT = 5, 1500, 120, 30
ARCH_NAME = {'riscv': 'RISC-V', 'loongarch': 'LoongArch'}

TEMPLATE = """# 任务：把上游补丁迁移到{arch}

上游已经有了下面的补丁（参照补丁），{arch}还没有对应的修改。请判断{arch}需要做哪些修改，并写出补丁。

- 下面给出的{arch}文件是程序根据参照补丁中的文件路径、函数名、宏名和配置符号挑选的**候选文件**，不一定都需要改，也可能需要改其中没有的文件（可以新建或改名文件，目录中已有的文件名列在后面）。
- 代码是{arch}在迁移之前的版本。
{strategy}
## 输出格式

1. **需要的修改**：逐条写出{arch}要改什么，各对应参照补丁的哪一处；参照补丁中不需要迁移的部分，说明原因。
2. **补丁**：一个统一格式的补丁，放在```diff代码块中，用`diff --git a/<路径> b/<路径>`开头，路径相对于内核源码根目录，上下文行必须与给出的代码一致。
3. **需要核对的前提**：参照做法在{arch}上成立所依赖的条件，逐条列出，并写明你是否已在给出的代码中核对过。

## 一、参照补丁

{reference}

## 二、{arch}的候选文件（迁移之前）

{files}

## 三、候选文件所在目录中的文件

{listing}
"""
STRATEGY_BLOCK = """
## 修复策略（供参考）

{table}
"""


def load_labels():
    raw = (SAMPLES / 'labels_all.json').read_bytes()
    want = [l.split()[0] for l in (SAMPLES / 'labels_sha256.txt').read_text(encoding='utf-8').splitlines()
            if l.endswith('labels_all.json')][0]
    if hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit('labels_all.json changed after its SHA was recorded')
    return json.loads(raw.decode('utf-8'))


def material(r):
    return (SAMPLES.parent / ('replay_samples_20261105' if r['batch'] == 1 else 'replay_samples_more_20261105')
            / 'replay' / r['id'])


def ref_paths(r):
    return ['.', ':(exclude)arch'] if r['ref_arch'] == 'common' else [f'arch/{r["ref_arch"]}']


def names_from_reference(r):
    """Functions containing changed lines (both sides), #define names and Kconfig/CONFIG_ symbols of +/- lines."""
    names = set()
    for c in r['refs']:
        for f in CK.git('diff', '--name-only', c + '^', c, '--', *ref_paths(r)).split():
            text = CK.git('diff', '-U0', c + '^', c, '--', f)
            for side, rev in (('-', c + '^'), ('+', c)):
                if f.endswith(('.c', '.h')):
                    spans = CK.functions(rev, f)
                    for m in re.finditer(rf'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', text, re.M):
                        s0 = int(m.group(1) if side == '-' else m.group(3))
                        n = int((m.group(2) if side == '-' else m.group(4)) or 1)
                        names |= {fn for s, e, fn, _ in spans if s <= s0 + max(n, 1) - 1 and s0 <= e}
            for line in text.splitlines():
                if line[:1] in '+-' and not line.startswith(('+++', '---')):
                    names |= set(re.findall(r'#\s*define\s+([A-Za-z_]\w*)', line))
                    names |= set(re.findall(r'\bCONFIG_([A-Z0-9_]+)', line))
                    if 'Kconfig' in f:
                        names |= set(re.findall(r'\b([A-Z][A-Z0-9_]{3,})\b', line))
    return {n for n in names if len(n) > 3}


def candidates(r, base):
    target = r['target_arch']
    picked = []
    for c in r['refs']:
        for f in CK.git('diff', '--name-only', c + '^', c, '--', *ref_paths(r)).split():
            if f.startswith('arch/'):
                g = f'arch/{target}/' + f.split('/', 2)[2]
                if CK.git('cat-file', '-t', f'{base}:{g}').strip() == 'blob' and g not in picked:
                    picked.append(g)
    names = names_from_reference(r)
    hits = {}
    for n in sorted(names):
        files = CK.git('grep', '-l', '-w', n, base, '--', f'arch/{target}').split()
        files = [x.split(':', 1)[1] for x in files]
        if 0 < len(files) <= COMMON_LIMIT:
            for x in files:
                hits.setdefault(x, set()).add(n)
    for f, _ in sorted(hits.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if f not in picked:
            picked.append(f)
    picked = picked[:MAX_FILES]
    return picked, names, {f: sorted(hits.get(f, ())) for f in picked}


def file_block(base, f, names):
    text = CK.git('show', f'{base}:{f}')
    lines = text.splitlines()
    lang = 'c' if f.endswith(('.c', '.h', '.S')) else ''
    if len(lines) <= MAX_LINES:
        return f'### `{f}`\n\n```{lang}\n{text.rstrip()}\n```'
    spans = CK.functions(base, f)
    first = min((s for s, *_ in spans), default=MAX_HEAD)
    head = lines[:min(first - 1, MAX_HEAD)]
    keep = [(n, t) for s, e, n, t in spans if n in names or any(re.search(rf'\b{re.escape(x)}\b', t) for x in names)]
    local = {n: t for s, e, n, t in spans}
    called = []
    for _, t in keep:  # same-file functions the kept ones call directly (one level)
        for c in re.findall(r'\b([A-Za-z_]\w*)\s*\(', t):
            if c in local and c not in {n for n, _ in keep} and c not in called:
                called.append(c)
    keep = keep[:12] + [(c, local[c]) for c in called][:max(0, 12 - len(keep))]
    body = '\n\n'.join(t for _, t in keep)
    return (f'### `{f}`（共{len(lines)}行，已截取：文件开头{len(head)}行、包含相关名字的函数，以及它们在本文件中直接调用的函数）\n\n'
            f'```{lang}\n' + '\n'.join(head) + '\n\n/* ... */\n\n' + body + '\n```')


def reference_block(r):
    out = []
    for c in r['refs']:
        msg = [l for l in CK.git('log', '-1', '--format=%B', c).splitlines() if not TRAILER.match(l.strip())]
        while msg and not msg[-1].strip():
            msg.pop()
        out.append(f'### 提交 {c}\n\n```\n' + '\n'.join(msg) + '\n```')
    diff = (material(r) / 'reference.diff').read_text(encoding='utf-8')
    return '\n\n'.join(out) + '\n\n### 改动\n\n```diff\n' + diff.rstrip() + '\n```'


def main():
    split = sys.argv[1]
    rows = [r for r in load_labels() if r['split'] == split]
    index, cands = [], {}
    for r in rows:
        meta = json.loads((material(r) / 'meta.json').read_text(encoding='utf-8'))
        base = meta['base']
        files, names, why = candidates(r, base)
        cands[r['id']] = {'files': files, 'why': why, 'names': sorted(names)}
        listing = []
        for d in sorted({f.rsplit('/', 1)[0] for f in files}):
            entries = CK.git('ls-tree', '--name-only', f'{base}:{d}').split()
            listing.append(f'- `{d}/`：' + '、'.join(entries[:80]) + ('……' if len(entries) > 80 else ''))
        arch = ARCH_NAME[r['target_arch']]
        common = dict(arch=arch, reference=reference_block(r),
                      files='\n\n'.join(file_block(base, f, names) for f in files) or '（程序没有找到候选文件）',
                      listing='\n'.join(listing) or '（无）')
        s_text = TEMPLATE.format(strategy=STRATEGY_BLOCK.format(table=STRATEGY.strip()), **common)
        n_text = TEMPLATE.format(strategy='', **common)
        assert s_text.replace(STRATEGY_BLOCK.format(table=STRATEGY.strip()), '') == n_text
        for cond, text in (('S', s_text), ('N', n_text)):
            d = CALLS / f'M_{r["id"]}_{cond}'
            if d.exists():
                raise SystemExit(f'preserve {d}')
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'id': r['id'], 'cond': cond, 'split': split, 'chars': len(text)})
    (HERE / f'candidates_{split}.json').write_text(json.dumps(cands, indent=1) + '\n', encoding='utf-8')
    (HERE / f'prompt_index_{split}.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    for x in index:
        print(x['dir'], x['chars'])


if __name__ == '__main__':
    main()
