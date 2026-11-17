"""Prompts for L2 (criteria.md section 3): the version-1 review prompt (patch_rules_20261105/build_review.py) with
(1) code facts collected by fixed rules, (2) the evidence requirement and (3) P1/P2 version-2 output instead of
P1-P3. Facts, per changed function in order of first call: up to 12 callees whose definition has more than 4 lines
(arch/riscv, kernel, mm, lib, init, include; a callee that is a function-like macro is shown with the functions its
body calls, one level), each cut to 80 lines, plus the same-name function of the other 32/64 variant; then up to 10
call sites of every changed non-static function. Same versions and runs as version 1.
WSL (git); no model calls. Output: <CALLS>/L2_<series>_<tag>_r<k>/prompt.md and review_index.json.
"""
from pathlib import Path
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'patch_rules_20261105'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B1 = load('build_review_v1', PREV / 'build_review.py')
CK, PC = B1.CK, B1.PC
CTX4 = HERE.parent / 'rules_v4_tighten_20261103' / 'ctx4.py'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'patch_rules_v2_20261105'
STATES, RUNS = B1.STATES, B1.RUNS
PER_FUNC, MAX_LINES, MAX_SITES = 12, 80, 10
FACT_DIRS = ('arch/riscv', 'kernel', 'mm', 'lib', 'init', 'include')

RULES = """## 依据要求（必须遵守）

- 报告一个问题，必须引用本提示中给出的代码作为依据（补丁、改动后的函数、第三节的代码事实、参照补丁）。
- 否定程序检查（第五节）的某个标记，同样必须引用本提示中的代码，说明为什么它不成立。
- 依据如果是本提示中没有给出的代码，或者是“据我所知”“通常”，就不能据此报告问题，也不能据此否定标记，只能写“判断不了”，并说明还需要看哪段代码。
- 第三节的代码事实由程序按固定规则收集：被改函数调用的函数的实现，以及被改函数在仓库中的调用点。判断前先查这一节。"""


def cut(text):
    lines = text.splitlines()
    return '\n'.join(lines[:MAX_LINES] + ([f'/* ... 共{len(lines)}行，只列前{MAX_LINES}行 */'] if len(lines) > MAX_LINES else []))


class Facts:
    def __init__(self, sha):
        self.sha = sha
        C = self.C = load(f'ctx4_{sha[:8]}', CTX4)
        C.SNAP = sha
        idx, _ = C.build_index()
        C.INDEX.update(idx)

    def defs(self, name):
        return [d for d in self.C.INDEX.get(name, []) if d['path'].startswith(FACT_DIRS)
                and d['end'] - d['start'] + 1 > 4]

    def macro(self, name):
        hits = CK.git('grep', '-n', '-E', rf'^#define[[:space:]]+{name}\(', self.sha, '--', 'include', 'arch/riscv/include')
        for h in hits.splitlines()[:1]:
            _, path, line, _ = h.split(':', 3)
            text = CK.git('show', f'{self.sha}:{path}').splitlines()
            k = int(line) - 1
            body = [text[k]]
            while body[-1].rstrip().endswith('\\') and k + 1 < len(text) and len(body) < 15:
                k += 1
                body.append(text[k])
            return path, '\n'.join(body)
        return None

    def section(self, changed):
        shown, out = {n for _, n in changed}, []
        for path, name in sorted(changed):
            d = next((x for x in self.C.INDEX.get(name, []) if x['path'] == path), None)
            if not d:
                continue
            picked = 0
            for c in self.C.calls(d):
                if picked >= PER_FUNC or c.name in shown:
                    continue
                ds = self.defs(c.name)
                if ds:
                    shown.add(c.name)
                    picked += 1
                    for x in ds[:2]:
                        out.append(f'#### `{x["path"]}:{x["name"]}`（被`{name}`调用）\n\n```c\n{cut(x["text"])}\n```')
                    continue
                m = self.macro(c.name)
                if m:
                    shown.add(c.name)
                    picked += 1
                    out.append(f'#### 宏`{c.name}`（{m[0]}，被`{name}`调用）\n\n```c\n{m[1]}\n```')
                    for inner in sorted(set(re.findall(r'([A-Za-z_]\w*)\s*\(', m[1])) - {c.name} - shown):
                        for x in self.defs(inner)[:1]:
                            shown.add(inner)
                            out.append(f'#### `{x["path"]}:{x["name"]}`（宏`{c.name}`中调用）\n\n```c\n{cut(x["text"])}\n```')
            base = path.rsplit('/', 1)[-1]
            for a, b in (('64', '32'), ('32', '64')):
                if a in base:
                    other = path[:len(path) - len(base)] + base.replace(a, b)
                    for x in self.C.INDEX.get(name, []):
                        if x['path'] == other:
                            out.append(f'#### `{x["path"]}:{x["name"]}`（另一变体中的同名函数）\n\n```c\n{cut(x["text"])}\n```')
        sites = []
        for path, name in sorted(changed):
            d = next((x for x in self.C.INDEX.get(name, []) if x['path'] == path), None)
            if not d or re.search(r'(^|\W)static(\W|$)', d['head']):
                continue
            rows = []
            for h in CK.git('grep', '-n', '-E', rf'(^|[^A-Za-z0-9_]){name}[[:space:]]*\(', self.sha, '--', '*.c',
                            ':(exclude)tools', ':(exclude)Documentation').splitlines():
                _, p, line, text = h.split(':', 3)
                owner = next((n for s, e, n, _ in CK.functions(self.sha, p) if s <= int(line) <= e), None)
                if owner and owner != name:
                    rows.append(f'- `{p}:{line}`，在`{owner}`中：`{text.strip()[:160]}`')
                if len(rows) >= MAX_SITES:
                    break
            if rows:
                sites.append(f'#### `{name}`的调用点\n\n' + '\n'.join(rows))
        return '\n\n'.join(out) + ('\n\n### 被改函数的调用点\n\n' + '\n\n'.join(sites) if sites else '')


def checks_text(series, tag, changed):
    d = json.loads((HERE / 'results' / f'flags_{series}_{tag}.json').read_text(encoding='utf-8'))
    names, paths = {n for _, n in changed}, {p for p, _ in changed}
    rows = [f'- {f["rule"]} `{f["path"]}:{f["name"]}`：{f["reason"]}' for f in d['flags']
            if (f['rule'] == 'P1' and set(f['chain']) & names) or (f['rule'] == 'P2' and (f['name'] in names or f['path'] in paths))]
    return '\n'.join(rows) or '（无）'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    ref = B1.ref_text()
    index = []
    for series, tag in STATES:
        cj = json.loads((PREV.parent / 'patch_check_20261105' / 'results' / series / 'commits.json').read_text(encoding='utf-8'))
        sha = next(s['sha'] for s in cj['steps'] if f'step{s["step"]}' == tag)
        diff = CK.git('diff', cj['base'], sha, '--', 'arch/riscv', 'kernel', 'include').splitlines()
        changed = PC.changed_functions(cj['base'], sha)
        funcs = []
        for path, name in sorted(changed):
            t = next((t for s, e, n, t in CK.functions(sha, path) if n == name), None)
            if t:
                funcs.append(f'### `{path}:{name}`\n\n```c\n{t}\n```')
        text = B1.TEMPLATE.format(checklist=B1.CHECKLIST + '\n\n' + RULES, base=cj['base'][:12], diff='\n'.join(diff),
                                  functions='\n\n'.join(funcs), reference=ref, checks='见第五节')
        text = text.replace('## 三、参照补丁（x86部分）', '## 三、代码事实（程序收集）\n\n' + Facts(sha).section(changed)
                            + '\n\n## 四、参照补丁（x86部分）')
        text = text.replace('## 四、程序检查结果（P1–P3，只作参考）\n\n见第五节',
                            '## 五、程序检查结果（P1、P2第2版，只作参考）\n\n' + checks_text(series, tag, changed))
        text = text.replace('程序检查（P1–P3）的结果附在后面', '程序检查（P1、P2）的结果附在第五节')
        assert '## 五、' in text and '## 三、代码事实' in text and 'a370c2419e46' not in text
        for k in range(1, RUNS + 1):
            d = CALLS / f'L2_{series}_{tag}_r{k}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'series': series, 'tag': tag, 'run': k, 'chars': len(text)})
    (HERE / 'review_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(json.dumps([(x['dir'], x['chars']) for x in index]))


if __name__ == '__main__':
    main()
