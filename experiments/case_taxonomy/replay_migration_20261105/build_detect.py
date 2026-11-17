"""Detection prompts for the generated test patches (criteria.md section 4): the L2 review of
patch_rules_v2_20261105/build_review2.py with a mechanism checklist written for any architecture, the same evidence
requirement, the same code facts (callees of the changed functions, one macro level, the other 32/64 variant,
call sites of changed non-static functions; indexed over arch/<target> and the common directories), the reference
patch, and for RISC-V the program flags of rules_test.json (version-4 rules and P1/P2 version 2, new against T^).
One call per patch that applies at some level. WSL (git); no model calls.
Output: <CALLS>/D_<dir>/prompt.md and detect_index_test.json.
"""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B2 = load('build_review2', HERE.parent / 'patch_rules_v2_20261105' / 'build_review2.py')
EV = load('evaluate', HERE / 'evaluate.py')
BP = load('build_prompts', HERE / 'build_prompts.py')
CK, PC = B2.CK, B2.PC
CALLS = BP.CALLS

CHECKLIST = """按机制逐项检查（每一项都要看，没有问题的写“未发现”）：

1. **M5 执行上下文**：正方向，在关中断、关抢占、持自旋锁或中断处理中调用了会睡眠的函数；反方向，只在当前CPU上生效的操作（本核TLB或指令缓存刷新、fixmap、per-CPU数据）没有在不可迁移的上下文中进行。
2. **M10 同一约定**：参照补丁中的每处处理，迁移补丁中是否有对应；没有对应的，目标架构是否确实不需要。目标架构有多个变体或配置（例如32/64位、是否开启某个扩展）时，各变体是否都处理了。
3. **M10 前提是否成立**：参照做法依赖的前提（某个初始化已完成、某个寄存器或扩展存在、某个接口的语义相同），在目标架构上是否成立。参照架构有、目标架构多出来的情况（例如更宽的寄存器、更多的状态），是否也处理了。
4. **M7 数值与宽度**：常量、类型宽度、符号扩展、对齐和边界是否按目标架构的ABI；用户或客体可控的下标是否用`array_index_nospec`钳住。
5. **M3 映射与缓存维护**：修改页表或代码之后，TLB和指令缓存的维护是否完整。
6. **M4 内存顺序**：需要的屏障或原子操作是否齐全。
7. **M6 资源生命周期**：分配的资源在出错和释放路径上是否正确释放、只释放一次。
8. **M9 配置与构建条件**：Kconfig依赖、条件编译、编译选项是否正确；补丁是否能在相关配置下编译。
9. **其他**：以上没有覆盖、但会导致错误的问题。"""

TEMPLATE = """# 任务：审查一个迁移到{arch}的补丁

下面是一个迁移补丁：把上游的参照补丁迁移到{arch}。请按机制逐项检查迁移补丁中的错误，包括漏改的地方。

要求：
- 只报告会导致错误的问题：编译失败、运行出错、行为与参照补丁的意图不一致而造成错误、遗漏了必须的修改、资源泄漏、内核警告。不要因为“风格不同”或“可以更好”就报告；
- 每个问题写明是否需要运行才能确认；
- 程序检查的结果（如果有）附在第五节，只作参考，可能有误报，也可能漏报。

{checklist}

{rules}

## 输出格式

先按上面9项逐项写简短结论，然后输出一个JSON代码块：

```json
[{{"位置": "文件:函数", "机制": "M5/M10/M7/M3/M4/M6/M9/其他", "检查项": 1, "问题": "一句话", "依据": "引用代码行并说明", "需要运行确认": true}}]
```

没有问题时输出`[]`。

## 一、迁移补丁（相对迁移之前的{arch}代码）

```diff
{diff}
```

## 二、改动后的完整函数

{functions}

## 三、代码事实（程序收集）

{facts}

## 四、参照补丁

{reference}

## 五、程序检查结果（只作参考）

{checks}
"""


class Facts(B2.Facts):
    def __init__(self, sha, arch):
        self.sha = sha
        C = self.C = load(f'ctx4_{sha[:8]}', B2.CTX4)
        C.SNAP = sha
        C.DEF_DIRS = (f'arch/{arch}', 'kernel', 'mm', 'lib', 'init', 'include/linux', 'include/asm-generic')
        idx, _ = C.build_index()
        C.INDEX.update(idx)
        B2.FACT_DIRS = (f'arch/{arch}', 'kernel', 'mm', 'lib', 'init', 'include')
        self.arch = arch

    def macro(self, name):
        """build_review2's macro lookup with arch/<target>/include instead of arch/riscv/include."""
        hits = CK.git('grep', '-n', '-E', rf'^#define[[:space:]]+{name}\(', self.sha, '--', 'include',
                      f'arch/{self.arch}/include')
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


def checks_text(name, rules):
    rows = rules.get(name)
    if rows is None:
        return '（本架构没有可用的程序检查）'
    return '\n'.join(f'- {f["rule"]} `{f["function"]}`：{f["reason"]}' for f in rows) or '（无新标记）'


def main():
    if (HERE / 'detect_index_test.json').exists():
        raise SystemExit('preserve')
    labels = {r['id']: r for r in BP.load_labels()}
    commits = json.loads((HERE / 'commits_test.json').read_text(encoding='utf-8'))
    rules_path = HERE / 'rules_test.json'
    rules = json.loads(rules_path.read_text(encoding='utf-8')) if rules_path.exists() else {}
    index = []
    for x in json.loads((HERE / 'prompt_index_test.json').read_text(encoding='utf-8')):
        c = commits[x['dir']]
        if not c['sha']:
            continue
        r = labels[x['id']]
        arch = r['target_arch']
        diff = CK.git('diff', c['base'], c['sha'])
        changed = PC.changed_functions(c['base'], c['sha'])
        funcs = []
        for path, name in sorted(changed):
            t = next((t for s, e, n, t in CK.functions(c['sha'], path) if n == name), None)
            if t:
                funcs.append(f'### `{path}:{name}`\n\n```c\n{t}\n```')
        text = TEMPLATE.format(arch=BP.ARCH_NAME[arch], checklist=CHECKLIST, rules=B2.RULES, diff=diff.rstrip(),
                               functions='\n\n'.join(funcs) or '（补丁没有改动C函数）',
                               facts=Facts(c['sha'], arch).section(changed) or '（无）',
                               reference=BP.reference_block(r), checks=checks_text(x['dir'], rules))
        d = CALLS / f'D_{x["dir"]}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'patch': x['dir'], 'id': x['id'], 'cond': x['cond'], 'chars': len(text)})
        print(d.name, len(text), flush=True)
    (HERE / 'detect_index_test.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
