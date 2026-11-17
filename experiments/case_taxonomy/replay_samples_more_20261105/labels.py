"""First annotator's labels for the 112 commits of pools RV2 and LA2 (criteria.md; definitions from
replay_samples_20261105/criteria.md), written after reading every message and the diffs of candidates, with every
reference checked by git show. Commits touching more than one architecture are labelled multi_arch by the program.
Then merges the 16 pairs of the first batch, freezes labels.json and labels_all.json (SHA in labels_sha256.txt) and
splits the merged pairs (criteria section 3). WSL (git); no model calls.
"""
from pathlib import Path
import hashlib
import json
import random
import subprocess

HERE = Path(__file__).resolve().parent
FIRST = HERE.parent / 'replay_samples_20261105'
REPO = '/root/repos/linux'
TOO_LARGE = 300

# id: (kind, refs, ref_arch, mechanism, found_by, reason)
PAIRS = {
    'V007': ('A', ['8c86405f606c', '41b87599c743'], 'x86', 'M7', '说明点名',
             'KVM中客体可控的下标在检查之后用array_index_nospec钳住；x86 ioapic、arm64 vgic的同类修复'),
    'V011': ('A-feature', ['fcc5bf89635a'], 'arm64', 'M10', '按文件查找',
             'KVM的mmu_lock由自旋锁改为读写锁，只读路径取读锁；arm64先做了同样的转换'),
    'A018': ('A', ['c8ebf64eab74'], 'arm64', 'M10', '说明点名',
             '模块重定位改用got/plt节的下标而不是指针，以便livepatch等延迟重定位；与arm64的修复方法相同'),
    'A024': ('A', ['f5c6d0fcf90c'], 'arm64', 'M10', '说明点名（说明中的提交号有误，按标题找到）',
             '模块的plt/got节地址置0，避免打印错误的符号地址；arm64的同名修复'),
    'A025': ('A-feature', ['5777eaed566a'], 'arm64', 'M10', '说明提到arm64，按文件查找',
             '用8字节访问优化校验和，代码来自arm64'),
    'A026': ('A-feature', ['42d038c4fb00', 'ee55ff803b38'], 'arm64', 'M10', '说明点名',
             '支持函数错误注入：实现regs_set_return_value()和override_function_with_return()'),
    'A028': ('A-feature', ['b57c2f124098', 'f3a112c0c40d'], 'riscv', 'M10', '说明点名',
             '用rethook替换kretprobe，主要参照RISC-V的实现'),
    'A029': ('A-feature', ['9732cafd9dc0'], 'arm64', 'M10', '说明提到arm64，按文件查找',
             '按arm64的写法实现jump label'),
    'A032': ('A', ['379eb01c2179'], 'riscv', 'M10', '说明点名',
             '生成core dump前先把当前进程的FP/SIMD寄存器保存到thread中；移植自RISC-V的修复'),
    'A039': ('A-feature', ['4e90d0522a68'], 'riscv', 'M9', '说明点名',
             '已支持静态开关后，选上HAVE_PREEMPT_DYNAMIC_KEY即可支持PREEMPT_DYNAMIC；RISC-V先做了同样的事'),
    'A048': ('A-feature', ['87f81e66e2e8', 'd0637c505f8a'], 'riscv', 'M9', '说明点名',
             '支持透明大页时选上THP_SWAP；RISC-V、arm64先做了'),
    'A051': ('A-feature', ['c862626e19ef'], 'arm64', 'M10', '说明提到arm64，按文件查找',
             'KVM支持KVM_DIRTY_LOG_INITIALLY_SET；arm64先实现'),
    'A052': ('A-feature', ['5cf896fb6be3'], 'arm64', 'M10', '说明点名',
             '内核自重定位支持RELR格式；arm64先实现'),
    'A059': ('A-feature', ['0e3f3649d44b', '61ae1321f06c'], 'riscv', 'M9', '说明点名',
             '选上GENERIC_CPU_VULNERABILITIES；RISC-V、arm64先做了'),
    'A060': ('A', ['7f0b1bf04511'], 'arm64', 'M4', '说明点名',
             '开启硬件页表遍历时，修改页表后要加屏障，避免推测访问造成内核态的虚假缺页；arm64的同类修复'),
    'A063': ('A', ['9090825fa997', '2c0d278f3293'], 'arm64', 'M5', '说明点名',
             'PREEMPT_RT下KVM的定时器hrtimer要标为硬中断中到期；arm64、x86的同类修复'),
    'A073': ('A', ['406f992e4a37'], 'x86', 'M10', '说明点名',
             '从休眠恢复时让非引导CPU用轮询的play_dead，避免IPI处理破坏idle任务的栈；与x86的修复相似'),
    'A077': ('A', ['48f6430505c0'], 'arm64', 'M9', '说明点名',
             'vDSO链接去掉--hash-style=sysv；照arm64的修改'),
    'A082': ('A', ['d02198550423'], 'x86', 'M5', '说明点名',
             '内核态使用FPU期间不能发生cond_resched，改用local_bh_disable保护；与x86的修复相似'),
    'A087': ('A-feature', ['61fc1ee8be26'], 'riscv', 'M7', '说明点名',
             '增大COMMAND_LINE_SIZE；RISC-V先做了同样的修改（取值不同）'),
    'A090': ('A', ['929adf8838f7'], 'arm64', 'M3', '说明提到arm64、RISC-V，按文件查找',
             'bpf_arch_text_copy已经刷新指令缓存，JIT中多余的bpf_flush_icache删掉；arm64先删'),
    'A093': ('B', ['eb7622d908a0'], 'riscv', 'M8', '说明点名',
             'kexec_file的通用代码已打印装载位置，架构自己的打印函数删掉；RISC-V在同一改动中先做了'),
    'A102': ('A-feature', ['35b3515be0ec'], 'riscv', 'M10', '说明提到RISC-V，按文件查找',
             'BPF trampoline支持fsession，逻辑与RISC-V JIT几乎相同'),
    'A103': ('A-feature', ['2ddec2c80b44'], 'riscv', 'M10', '说明点名',
             'JIT内联bpf_get_smp_processor_id()；RISC-V先实现'),
    'A104': ('A-feature', ['2bb138cb20a6'], 'arm64', 'M10', '说明点名',
             'JIT内联bpf_get_current_task/_btf()；arm64先实现'),
    'A109': ('A-feature', ['f3336b48cf9d'], 'riscv', 'M10', '说明点名',
             '定义DIRECT_MAP_PHYSMEM_END，限制直接映射的物理地址上限；RISC-V先定义'),
}
NON = {
    'build': ('只修编译、链接或编译器警告', ['V000', 'A042']),
    'no_effect': ('注释、清理或配置文件，没有功能上的缺陷', ['V001', 'V002', 'V003', 'V005', 'V009', 'A086', 'A110']),
    'no_ref': ('提到其他架构，但找不到处理同一条件、早于T的具体提交', [
        'V004', 'V006', 'V008', 'V010', 'A016', 'A021', 'A034', 'A040', 'A047', 'A054', 'A058', 'A072', 'A076',
        'A101', 'A108']),
    'arch_only': ('只与目标架构自身有关', ['A056', 'A057']),
    'common': ('主要是公共代码的改动，目标架构只是随之调整', ['A045']),
}
NOTES = {
    'A076': 'RISC-V把ret_from_fork移到C的f955aa8723a6与T的提交时间相同，不早于T',
    'A086': '去掉-nostdlib是整理，说明列出的是其他架构改用$(LD)链接的提交，不是同一修改',
    'V002': '去掉写死的0x800是整理，参照的x86提交是2007年的布局调整',
}


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def arch_lines(sha, arch):
    stat = [l.split('\t') for l in git('show', '--numstat', '--format=', sha, '--', f'arch/{arch}').splitlines() if l]
    return sum(int(a) + int(b) for a, b, _ in stat if a.isdigit() and b.isdigit()), len(stat)


def main():
    if (HERE / 'labels.json').exists():
        raise SystemExit('preserve')
    pool = json.loads((HERE / 'items.json').read_text(encoding='utf-8'))
    reason_of = {i: (k, txt) for k, (txt, xs) in NON.items() for i in xs}
    rows = []
    for it in pool:
        i, arch = it['id'], 'riscv' if it['source'] == 'RV2' else 'loongarch'
        arches = {f.split('/')[1] for f in it['files'] if f.startswith('arch/')}
        row = {'id': i, 'source': it['source'], 'commit': it['commit'], 'target_arch': arch, 'subject': it['subject']}
        if i in PAIRS:
            kind, refs, ref_arch, mech, found_by, reason = PAIRS[i]
            for r in refs:
                assert git('cat-file', '-t', r).strip() == 'commit', r
                assert int(git('log', '-1', '--format=%ct', r)) < int(git('log', '-1', '--format=%ct', it['commit'])), (i, r)
            lines, files = arch_lines(it['commit'], arch)
            row.update({'pair': True, 'kind': kind, 'refs': refs, 'ref_arch': ref_arch, 'mechanism': mech,
                        'simple': lines <= 40 and files <= 2, 'too_large': lines > TOO_LARGE, 'target_lines': lines,
                        'target_files': files, 'found_by': found_by, 'reason': reason})
        elif len(arches) > 1:
            assert i not in reason_of, i
            row.update({'pair': False, 'category': 'multi_arch', 'reason': 'T本身同时改动多个架构'})
        else:
            cat, txt = reason_of[i]
            row.update({'pair': False, 'category': cat, 'reason': NOTES.get(i, txt)})
        rows.append(row)
    text = json.dumps(rows, indent=1, ensure_ascii=False) + '\n'
    (HERE / 'labels.json').write_text(text, encoding='utf-8')
    first = json.loads((FIRST / 'labels.json').read_text(encoding='utf-8'))
    merged = [dict(r, batch=1) for r in first if r['pair']] + [dict(r, batch=2) for r in rows if r['pair']]
    merged.sort(key=lambda r: r['id'])
    test_ids = {r['id'] for r in merged}
    dev = set(random.Random(20261105).sample(sorted(test_ids), len(merged) // 4))
    for r in merged:
        r['split'] = 'dev' if r['id'] in dev else 'test'
    all_text = json.dumps(merged, indent=1, ensure_ascii=False) + '\n'
    (HERE / 'labels_all.json').write_text(all_text, encoding='utf-8')
    (HERE / 'labels_sha256.txt').write_text(
        f'{hashlib.sha256(text.encode()).hexdigest()}  labels.json\n{hashlib.sha256(all_text.encode()).hexdigest()}  labels_all.json\n',
        encoding='utf-8')
    cats = {}
    for r in rows:
        cats[r.get('category', 'pair')] = cats.get(r.get('category', 'pair'), 0) + 1
    print(cats, '| merged pairs', len(merged), 'dev', len(dev), '| simple', sum(r['simple'] for r in merged),
          '| batch2 by source', {s: sum(r['source'] == s for r in rows if r['pair']) for s in ('RV2', 'LA2')})


if __name__ == '__main__':
    main()
