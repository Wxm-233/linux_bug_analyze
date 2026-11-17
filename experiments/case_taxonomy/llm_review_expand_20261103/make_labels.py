"""Write labels.json (criteria.md section 2) from the first annotator's per-candidate decisions below, made by reading
each function at its snapshot and the commits of evidence_la.json before any prompt was built. No git, no model."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
N2 = 'noinstr入口中的调用发生在irqentry_enter之后，上下文已建立；LoongArch不做noinstr的objtool校验，上游到终点版本一直保留这种写法（终点版本arch/loongarch中除bug.h外没有instrumentation_begin）'
RT = '该快照的LoongArch还不能开启PREEMPT_RT（ARCH_SUPPORTS_RT从v6.13起才有，be2ea982bb83），普通自旋锁不会睡眠'
FIXED = {
    24: ('bb0511d59db9', 'noinstr代码调用的regs_irqs_disabled只是static inline；修复（带Fixes标签）把它改为__always_inline，与参照架构一致'),
    27: ('ea68d444a658', 'setup_arch中先调用parse_early_param，而jump_label_init在其后（start_kernel中）才执行，早期参数处理改静态键会出错；修复把jump_label_init移到parse_early_param之前，说明中写“与其他架构的做法相同”'),
    28: ('69cc6fad5df4', 'do_ale不开中断，用户态的非对齐访问路径中show_registers/emulate_load_store_insn会调用get_user，可能睡眠；修复在中断原本开启时打开中断，正是“关中断时调用可能睡眠的函数”'),
    46: ('b3e31a6650d4', 'KVM_CAP_NR_VCPUS直接返回num_online_cpus()，参照架构都用min_t限制在KVM_MAX_VCPUS以内；修复改为min_t，说明中写“其他架构已经这样做”'),
    51: ('47256c4c8b1b', '持自旋锁时调用copy_from_user，可能睡眠；修复标题即“Avoid copy_*_user() with lock hold”'),
    52: ('62f11796a0df', '持自旋锁时调用copy_from_user；同上'),
    53: ('01a8e68396a6', '持自旋锁时调用copy_from_user；同上'),
    54: ('8dc5245673cf', '持自旋锁时调用copy_from_user；同上'),
    55: ('8dc5245673cf', '持自旋锁时调用copy_to_user；与54为同一函数、同一修复'),
}
A2 = {
    49: '下标cpuid来自客体（exit.c中由客体寄存器算出），检查上界后直接访问phys_map，没有array_index_nospec，到终点版本仍未加；2db06c15d8c7修的是负数下标的越界，不是推测执行，所以不作为修复依据',
    50: '下标val来自用户态（KVM_SET_ONE_REG写CPUID），检查上界后访问phys_map，没有array_index_nospec，到终点版本仍未加',
}
C = {23: 'noinstr代码调用的on_thread_stack只是static inline，参照架构为__always_inline；后来a45728fd4120在启用STACKLEAK时顺带改为__always_inline，说明中没有提到noinstr，难以判断是否算修复'}
B = {
    0: 'die只在内核态出错时调用，show_stacktrace按user_mode(regs)取内核栈，不会走get_user',
    15: '开中断取决于父上下文：从用户态或开中断的内核进入时已先开中断；关中断的内核上下文访问用户地址在各架构都是同样处理，不是LoongArch特有问题',
    20: '崩溃转储路径：panic/die已调用bust_spinlocks置oops_in_progress，smp_call_function不等待（wait=0），关中断调用在此场合是允许的',
    21: 'console_flush_on_panic先把console_may_schedule清零，console_unlock不会cond_resched',
    22: '关机路径中do_kernel_power_off注销的是atomic通知链上的处理函数，不会走down_write；参照架构的machine_power_off也同样在关抢占后调用',
    25: 'v6.1的LoongArch异常表还没有type字段，没有switch，不需要BUG()兜底',
    26: 'LoongArch不支持PAGE_TABLE_CHECK（Kconfig中没有ARCH_SUPPORTS_PAGE_TABLE_CHECK），不调用检查函数没有影响',
    40: 'LoongArch休眠恢复走直接映射窗口，不需要为临时页表申请安全页',
    44: RT + '；hrtimer_cancel_wait_running只在PREEMPT_RT下才拿锁',
    45: RT + '；hrtimer_cancel_wait_running只在PREEMPT_RT下才拿锁',
    47: '参照架构在vcpu_load中发的请求对应LoongArch当时还没有的功能（如半虚拟化计时），缺少功能不算缺陷',
    48: '参照架构调用的是BPF prog pack分配器，LoongArch当时还没有采用这一功能（后来4ab17e762b34作为新功能加入），缺少功能不算缺陷',
    56: 'LoongArch用kvm_arch_irqchip_in_kernel做了同样的检查',
    57: 'suspend_disable_secondary_cpus就是对freeze_secondary_cpus的封装，效果相同',
    58: 'show_cpuinfo对不在线的CPU直接返回，不需要在c_start中跳过',
}


def main():
    if (HERE / 'labels.json').exists():
        raise SystemExit('preserve')
    rows = json.loads((HERE / 'candidates_la.json').read_text(encoding='utf-8'))['rows']
    out = []
    for c in rows:
        k = c['cand']
        if k in FIXED:
            lab = {'label': 'a', 'basis': 'fixed_upstream', 'fix': FIXED[k][0], 'label_reason': FIXED[k][1]}
        elif k in A2:
            lab = {'label': 'a2', 'basis': 'first_annotator', 'fix': None, 'label_reason': A2[k]}
        elif k in C:
            lab = {'label': 'c', 'basis': 'first_annotator', 'fix': None, 'label_reason': C[k]}
        elif k in B:
            lab = {'label': 'b', 'basis': 'first_annotator', 'fix': None, 'label_reason': B[k]}
        elif c['kind'] == 'noinstr':
            lab = {'label': 'b', 'basis': 'first_annotator', 'fix': None, 'label_reason': N2}
        elif c['kind'] == 'rt':
            lab = {'label': 'b', 'basis': 'first_annotator', 'fix': None,
                   'label_reason': RT + '；而且只有父上下文本来就关中断时，这里才在关中断状态下调用force_sig*'}
        else:
            raise SystemExit(f'no decision for {k}')
        out.append({**c, **lab})
    note = ('第一标注人（模型Claude）在生成任何提示词之前定的标签：逐条阅读快照代码与evidence_la.json中的后来提交。'
            'a=上游修复依据；a2=疑似真问题无修复；b=误报；c=判断不了。评分只用a与b（criteria.md第二节）。')
    (HERE / 'labels.json').write_text(json.dumps({'note': note, 'rows': out}, indent=1, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
    from collections import Counter
    print(Counter(r['label'] for r in out), Counter((r['label'], r['rule']) for r in out))


if __name__ == '__main__':
    main()
