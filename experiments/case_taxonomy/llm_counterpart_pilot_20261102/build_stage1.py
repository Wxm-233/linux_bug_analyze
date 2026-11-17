"""Reference pool and step-1 prompts (criteria.md sections 1-2). WSL. Output: refs.json, stage1_index.json and
<CALLS>/s1_<sha12>/prompt.md. No model calls here.
"""
import json

from common import CALLS, HERE, REF_ARCHES, W_END, W_START, git, message

TEMPLATE = '''你是Linux内核跨架构问题的分析助手。下面是一个在arm64、x86或LoongArch上（或同时改动公共代码与这些架构）的内核提交。

请判断：这个提交修的或改的，是不是**其他架构（包括RISC-V）也必须遵守的要求**？例如：公共接口或钩子的语义（参数、返回值、调用上下文、调用顺序）、公共代码对架构的假设、各架构都必须遵守的硬件或软件规则（如改写代码后维护指令缓存、释放页表后刷新TLB、在原子上下文中不能睡眠）。

如果它只与该架构自己的硬件、特有功能、性能优化、新功能、代码整理有关，回答no。拿不准回答unsure。

只根据下面的材料判断，最后输出一个JSON对象（不要有其他JSON）：
{{"shared": "yes|no|unsure", "requirement": "一句话写出这条要求（no时可留空）", "why": "一句话理由"}}

【标题】
{subject}

【提交说明】
{message}

【改动统计】
{stat}
'''


def pool():
    def shas(*args):
        return set(git('log', '--no-merges', '--format=%H', f'--since={W_START}', f'--until={W_END}', 'df2908090cda',
                       *args).split())
    riscv = shas('--', 'arch/riscv')
    p1 = shas('--grep=Fixes:', '--', *REF_ARCHES) - riscv
    other = shas('--', *REF_ARCHES)
    common = shas('--', '.', ':(exclude)arch', ':(exclude)tools', ':(exclude)Documentation')
    p2 = (other & common) - riscv
    return p1, p2


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    p1, p2 = pool()
    refs = []
    for sha in sorted(p1 | p2):
        date = git('log', '-1', '--format=%cI', sha).strip()
        refs.append({'sha': sha, 'id': sha[:12], 'date': date, 'subject': git('log', '-1', '--format=%s', sha).strip(),
                     'P1': sha in p1, 'P2': sha in p2})
    refs.sort(key=lambda r: (r['date'], r['sha']))
    (HERE / 'refs.json').write_text(json.dumps(refs, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    index = []
    for r in refs:
        d = CALLS / f's1_{r["id"]}'
        d.mkdir(parents=True)
        stat = git('show', '--format=', '--stat=100', r['sha']).rstrip().splitlines()
        stat = '\n'.join(stat[-25:])
        (d / 'prompt.md').write_text(TEMPLATE.format(subject=r['subject'], message=message(r['sha']), stat=stat),
                                     encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'id': r['id']})
    (HERE / 'stage1_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(refs), 'refs', sum(r['P1'] for r in refs), 'P1', sum(r['P2'] for r in refs), 'P2')


if __name__ == '__main__':
    main()
