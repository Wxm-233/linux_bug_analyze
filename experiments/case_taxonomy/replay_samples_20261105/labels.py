"""First annotator's labels for the 159 pool commits (criteria.md sections 2 and 3), written after reading each
commit's message (all) and diff (candidates and borderline ones) and checking every reference with git show.
`simple` is computed from T's diff in the target architecture (criteria section 3). WSL (git); no model calls.
Output: labels.json (frozen; SHA in labels_sha256.txt).
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / 'fix_strategy_test_20261105' / 'items.json'
REPO = '/root/repos/linux'

# id: (kind, refs, ref_arch, mechanism, found_by, reason)
PAIRS = {
    'R012': ('A', ['7616fc8bcd7e'], 'arm64', 'M10', '说明点名',
             '补丁后的alternative指令位于另一节，jal的PC相对偏移要按新位置修正；arm64在alternative中对立即数跳转做了同样的修正'),
    'R014': ('A', ['588a513d3425'], 'arm64', 'M4', '说明点名',
             'flush_icache_pte中先测试再置PG_dcache_clean，刷新之后才置位；与arm64 __sync_icache_dcache的修复逐行相同'),
    'R046': ('A', ['97b6b9cbba40'], 'x86', 'M9', '同一系列',
             'purgatory去掉PGO编译选项，避免生成多个.text节；x86同一系列的修改逐行相同'),
    'R048': ('A', ['91218d7d708e'], 'x86', 'M9', '同一系列',
             'purgatory的sha256.o加-D__NO_FORTIFY，避免fortify误报；x86的修改逐行相同'),
    'R050': ('A', ['24cc61d8cb5a'], 'arm64', 'M10', '说明点名',
             'memblock_allow_resize()要等线性映射建好之后再调用；arm64早先做了同样的调整'),
    'R064': ('A', ['6460d3201471'], 'arm64', 'M4', '按文件查找',
             'readX()之后的delay()必须排在读完成之后；arm64在__iormb中处理了同一条件，做法不同（RISC-V在fence中加I位）'),
    'R077': ('B', ['fdc268232dbb'], 'arm64', 'M8', '按文件查找',
             '改用通用crashkernel预留接口后，通用代码已把crashk_res插入iomem_resource，架构代码不能再插一次；arm64、x86转换时删掉了自己的插入，RISC-V漏了'),
    'L081': ('A', ['694896ad3ca7', 'bb0a1d6b49cb'], 'riscv', 'M7', '同一系列',
             'ALU32的符号扩展mov要清掉高32位；RISC-V、arm64实现该指令时已处理'),
    'L082': ('A', ['83cc63afab71', '1104247f3f97'], 'riscv', 'M7', '同一系列',
             '无条件bswap32要清掉高32位；RISC-V、arm64实现该指令时已处理'),
    'L093': ('B', ['85fcde402db1'], 'common', 'M8', '按文件查找',
             'crashkernel预留代码拆出为CRASH_RESERVE后，其他架构在同一提交中改了Kconfig和头文件名，LoongArch漏了'),
    'L112': ('B', ['57fbad15c2ee'], 'common', 'M8', '同一系列',
             'STACKLEAK改名为KSTACK_ERASE时，arm64等的入口代码同步改了条件宏，LoongArch的stackframe.h漏了'),
    'L121': ('A', ['fd2e08128944'], 'riscv', 'M7', '同一系列',
             'struct_ops trampoline的返回值要按原生ABI做符号扩展；RISC-V先做了同样的修复，结构几乎相同'),
    'L123': ('A', ['eb707dde264a'], 'arm64', 'M10', '同一系列',
             'trampoline不支持结构体参数时要拒绝；arm64的同名修复相同'),
    'L128': ('A', ['443574b03387'], 'riscv', 'M7', '按文件查找',
             'kfunc调用是原生调用，参数要按原生ABI做符号扩展；RISC-V先做了同样的修复'),
    'L132': ('A', ['96b0f5addc7a'], 'arm64', 'M10', '按文件查找',
             'trampoline已用prog pack时，arch_protect_bpf_trampoline应返回0，否则通用实现会把pack设为只读；arm64改用prog pack时做了这一点'),
    'L147': ('A', ['369e4635d048'], 'riscv', 'M6', '同一系列',
             'bpf_jit_free在子程序JIT中途失败时要释放ctx.offset；RISC-V先做了同样的一行修复'),
}

# non-pairs by reason (criteria section 2, last list)
NON = {
    'build': ('只修编译、链接或编译器警告', [
        'R004', 'R007', 'R008', 'R013', 'R015', 'R019', 'R024', 'R035', 'R041', 'R042', 'R043', 'R045', 'R051', 'R052',
        'R057', 'R059', 'R071', 'R072', 'R074', 'L079', 'L084', 'L088', 'L094', 'L097', 'L099', 'L101', 'L103', 'L109',
        'L115', 'L119', 'L120', 'L134', 'L140', 'L145', 'L155']),
    'multi_arch': ('T本身同时改动多个架构', ['R023', 'R031', 'R044', 'R067']),
    'no_effect': ('注释、清理或配置文件，没有功能上的缺陷', ['R009', 'L100', 'L102', 'L110', 'L131', 'L141']),
    'no_ref': ('跨架构，但找不到处理同一条件的具体参照提交', [
        'R000', 'R027', 'R061', 'L080', 'L085', 'L086', 'L104', 'L118', 'L126', 'L136', 'L146']),
}
NOTES = {
    'R000': 'arm64 4d1c2ee2709f把ret_to_user移到C是无功能变化的整理，不是同一问题的修复',
    'L080': '说明写“像其他架构那样”去掉返回值符号扩展，但其他架构从来没有这样做，没有具体的修复提交',
    'L118': '同一系列中其他架构转换为通用TIF位时编号正确，但T是修LoongArch自己转换时的编号错误，不是跟进',
    'L120': 'RISC-V有同名修复d0bf7cd5df18，但两者都只消除静态检查警告，说明写明原逻辑正确',
    'L136': '同类修改（s390）晚于T',
}


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def simple(sha, arch):
    stat = [l.split('\t') for l in git('show', '--numstat', '--format=', sha, '--', f'arch/{arch}').splitlines() if l]
    lines = sum(int(a) + int(b) for a, b, _ in stat if a.isdigit() and b.isdigit())
    return lines <= 40 and len(stat) <= 2, lines, len(stat)


def main():
    if (HERE / 'labels.json').exists():
        raise SystemExit('preserve')
    pool = json.loads(POOL.read_text(encoding='utf-8'))
    ids = {it['id'] for it in pool}
    listed = set(PAIRS) | {i for _, xs in NON.values() for i in xs}
    reason_of = {i: (k, txt) for k, (txt, xs) in NON.items() for i in xs}
    rows = []
    for it in pool:
        i, arch = it['id'], 'riscv' if it['source'] == 'R' else 'loongarch'
        row = {'id': i, 'commit': it['commit'], 'target_arch': arch, 'subject': it['subject']}
        if i in PAIRS:
            kind, refs, ref_arch, mech, found_by, reason = PAIRS[i]
            for r in refs:
                assert git('cat-file', '-t', r).strip() == 'commit', r
                assert int(git('log', '-1', '--format=%ct', r)) < int(git('log', '-1', '--format=%ct', it['commit'])), (i, r)
            ok, lines, files = simple(it['commit'], arch)
            row.update({'pair': True, 'kind': kind, 'refs': refs, 'ref_arch': ref_arch, 'mechanism': mech,
                        'simple': ok, 'target_lines': lines, 'target_files': files, 'found_by': found_by,
                        'reason': reason})
        else:
            cat, txt = reason_of.get(i, ('arch_only', '只与目标架构自身有关'))
            row.update({'pair': False, 'category': cat, 'reason': NOTES.get(i, txt)})
        rows.append(row)
    assert listed <= ids, listed - ids
    text = json.dumps(rows, indent=1, ensure_ascii=False) + '\n'
    (HERE / 'labels.json').write_text(text, encoding='utf-8')
    (HERE / 'labels_sha256.txt').write_text(hashlib.sha256(text.encode('utf-8')).hexdigest() + '  labels.json\n',
                                            encoding='utf-8')
    pairs = [r for r in rows if r['pair']]
    print(len(pairs), 'pairs;', sum(r['simple'] for r in pairs), 'simple;',
          {k: sum(r.get('category') == k for r in rows) for k in ('arch_only', 'build', 'multi_arch', 'no_effect', 'no_ref')})


if __name__ == '__main__':
    main()
