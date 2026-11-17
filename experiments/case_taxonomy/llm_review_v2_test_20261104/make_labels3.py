"""Write labels3.json (criteria.md section 4) from the first annotator's decisions below, made by reading each function
at its snapshot and the commits of evidence_L.json / evidence_M.json before any prompt was built. No git, no model.
Each decision is (label3, basis3, reason[, fix commit]); basis3: fixed_upstream, first_annotator_nofix,
first_annotator; label3 unsure is left out of the metrics."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
NOINSTR_LA = ('noinstr入口中的调用发生在irqentry_enter之后，上下文已建立；LoongArch不做noinstr的objtool校验，'
              '上游到终点版本一直保留这种写法（与开发样本的同类标签一致）')
RT_LA = '该快照的LoongArch还不能开启PREEMPT_RT（ARCH_SUPPORTS_RT从v6.13起才有，be2ea982bb83），普通自旋锁不会睡眠'
PIE_LA = ('入口先按PIE恢复异常前的中断状态；从用户态进入时中断已打开，get_user可以睡眠；'
          '内核态时__get_inst用get_kernel_nofault，不会睡眠')
L = {
    'L00': ('not_issue', 'first_annotator', '标记的是bust_spinlocks(1)，它只把oops_in_progress加1；console_unblank只在bust_spinlocks(0)中调用，'
            '而且那时oops_in_progress不为0，走down_trylock_console_sem，不会睡眠'),
    'L01': ('not_issue', 'first_annotator', RT_LA),
    'L02': ('unsure', 'first_annotator', 'panic路径先bust_spinlocks(1)，smp_call_function不报警告；machine_halt/restart/power_off只关抢占、未关中断。'
            '但sysrq-b在键盘中断中调用emergency_restart→machine_restart→smp_send_stop，此时关中断且oops_in_progress为0，'
            '开启lockdep时会触发lockdep_assert_irqs_enabled；这算不算实际错误拿不准'),
    'L03': ('convention', 'first_annotator', NOINSTR_LA),
    'L04': ('convention', 'first_annotator', NOINSTR_LA),
    'L05': ('bug', 'fixed_upstream', 'do_ale不开中断，用户态非对齐访问路径中emulate_load_store_insn调用get_user，可能睡眠；'
            '修复在中断原本开启时打开中断（与开发样本28为同一函数、同一修复）', '69cc6fad5df4'),
    'L06': ('convention', 'first_annotator', NOINSTR_LA),
    'L07': ('convention', 'first_annotator', 'canary由get_random_bytes异或LINUX_VERSION_CODE得到，没有像get_random_canary那样把最低字节清零，'
            '防字符串溢出泄露的能力弱一些，但不会造成实际错误；上游后来改为get_random_canary，说明为“Like others”', 'a28547576b3b'),
    'L08': ('not_issue', 'first_annotator', PIE_LA),
    'L09': ('convention', 'first_annotator', NOINSTR_LA),
    'L10': ('convention', 'first_annotator', NOINSTR_LA),
    'L11': ('convention', 'first_annotator', NOINSTR_LA),
    'L12': ('not_issue', 'first_annotator', '内核态先die_if_kernel；' + PIE_LA),
    'L13': ('convention', 'first_annotator', NOINSTR_LA),
    'L14': ('convention', 'first_annotator', NOINSTR_LA),
    'L15': ('not_issue', 'first_annotator', '__do_page_fault按PIE开中断：从用户态或开中断的内核进入时已先开中断；faulthandler_disabled或没有mm时'
            '直接返回，不进handle_mm_fault；关中断的内核上下文访问用户地址在各架构都是同样处理（与开发样本15的标签一致）'),
    'L16': ('convention', 'first_annotator', NOINSTR_LA),
    'L17': ('bug', 'first_annotator_nofix', '下标csr来自客体指令（exit.c的csrid）或用户态（KVM_GET/SET_ONE_REG的id），检查上界后直接读gcsr_flag，'
            '没有array_index_nospec，读出的值决定后续分支和对csrs[id]的访问；到终点版本仍未加（与开发样本49、50的标准一致）'),
    'L18': ('bug', 'fixed_upstream', '持spin_lock_irqsave时调用copy_to_user，可能睡眠（与开发样本52为同一函数、同一修复）', '62f11796a0df'),
    'L19': ('bug', 'fixed_upstream', '持spin_lock_irqsave时调用copy_to_user，可能睡眠（与开发样本53为同一函数、同一修复）', '01a8e68396a6'),
    'L20': ('not_issue', 'first_annotator', 'LoongArch没有通用的irqchip_mode，kvm_arch_irqchip_in_kernel检查ipi、eiointc、pch_pic三个内核中断控制器都已创建，'
            '作用与参照架构的irqchip_in_kernel相同'),
    'L21': ('not_issue', 'first_annotator', 'schedule_work可在原子上下文中调用，不会睡眠；参照架构的__cpu_disable同样在关中断时调用irq_migrate_all_off_this_cpu'),
}
RT_MIPS = '到终点版本MIPS的Kconfig都没有select ARCH_SUPPORTS_RT，不能开启PREEMPT_RT，普通自旋锁不会睡眠'
NOINSTR_MIPS = 'MIPS没有select HAVE_NOINSTR_VALIDATION，objtool不校验noinstr，不会造成实际错误，只是与参照架构的写法不一致'
STI = ('genex.S中该处理函数的BUILD_HANDLER第三个参数为sti，入口已打开中断，从用户态进入时get_user/down_read可以睡眠；'
       '内核态时读的是内核正文，不会缺页')


def sti(extra=''):
    return ('not_issue', 'first_annotator', STI + extra)


def rt_sti():
    return ('not_issue', 'first_annotator', RT_MIPS + '；且该处理函数入口为sti，已开中断')


M = {
    'M00': ('not_issue', 'first_annotator', RT_MIPS),
    'M01': ('convention', 'first_annotator', 'v6.1的arch_cpu_idle没有__cpuidle/noinstr标注；' + NOINSTR_MIPS
            + '。上游26388a7c353f在所有架构上统一补了__cpuidle，属于写法统一', '26388a7c353f'),
    'M02': ('not_issue', 'first_annotator', '崩溃转储路径：panic已bust_spinlocks(1)置oops_in_progress，smp_call_function不等待（wait=0），'
            '关中断调用在此场合是允许的（与LoongArch开发样本20的标签一致）'),
    'M03': ('not_issue', 'first_annotator', '标记的是bust_spinlocks(1)，只把oops_in_progress加1，不调用console_unblank'),
    'M04': ('not_issue', 'first_annotator', 'MIPS中die只由die_if_kernel和mm/fault.c的no_context调用，regs都是内核态，'
            'show_registers按user_mode(regs)读内核栈和内核正文，不走get_user'),
    'M05': ('not_issue', 'first_annotator', 'do_ade的入口参数为ade（KMODE），保持异常前的中断状态：从用户态进入时中断已打开；'
            'fixup_exception只查异常表，不访问用户内存'),
    'M06': ('not_issue', 'first_annotator', 'do_ade入口为KMODE，从用户态进入时中断已打开，emulate_load_store_insn中get_user可以睡眠；'
            '关中断的内核上下文访问用户地址在各架构都是同样处理'),
    'M07': ('not_issue', 'first_annotator', 'do_ade入口为KMODE，从用户态进入时中断已打开；同M06'),
    'M08': ('not_issue', 'first_annotator', 'do_ade入口为KMODE，从用户态进入时中断已打开；show_registers只在unaligned_action为SHOW的调试选项下调用'),
    'M09': ('not_issue', 'first_annotator', 'do_be入口为cli，但exception_epc只在!user_mode(regs)时调用，读的是内核正文，不会缺页、不会睡眠'),
    'M10': sti(), 'M11': sti(), 'M12': sti(), 'M13': sti(), 'M14': rt_sti(), 'M15': sti(),
    'M16': rt_sti(), 'M17': ('not_issue', 'first_annotator', RT_MIPS + '；且do_gsexc入口参数为gsexc，已开中断'),
    'M18': ('unsure', 'first_annotator', 'do_mcheck入口为cli；用户态发生机器检查时，show_code走get_user，开启DEBUG_ATOMIC_SLEEP会报'
            '“在原子上下文中睡眠”警告，但紧接着就panic，这算不算实际错误拿不准'),
    'M19': rt_sti(), 'M20': rt_sti(), 'M21': sti(), 'M22': sti(), 'M23': rt_sti(), 'M24': sti(), 'M25': sti(),
    'M26': sti(), 'M27': sti(), 'M28': rt_sti(), 'M29': sti(),
    'M30': ('convention', 'first_annotator', NOINSTR_MIPS + '（e4de20576986修的是空指针，与此无关）'),
    'M31': ('not_issue', 'first_annotator', RT_MIPS),
    'M32': ('not_issue', 'first_annotator', RT_MIPS),
    'M33': ('not_issue', 'first_annotator', 'TX49的plat_ioremap对0xff000000起4MB的寄存器区直接映射，TX4938_TMR_REG(2)在此范围内，'
            'ioremap不会走get_vm_area，不会睡眠'),
    'M34': ('not_issue', 'first_annotator', '参照架构多出的是WARN_ON_ONCE(trap_nr != UPROBE_TRAP_NR)这一自检警告，缺少它不会造成错误'),
    'M35': ('not_issue', 'first_annotator', 'MIPS的异常表项没有type字段，fixup_exception没有switch，不需要BUG()兜底'),
    'M36': ('bug', 'first_annotator_nofix', 'arch_mem_init（由setup_arch调用）中执行parse_early_param，早于start_kernel中的jump_label_init；'
            'MIPS选了IRQ_FORCED_THREADING和HAVE_ARCH_JUMP_LABEL，启动参数threadirqs的setup_forced_irqthreads会调用static_branch_enable，'
            '触发“static key used before call to jump_label_init”警告；到终点版本仍未改（LoongArch的同一问题已由ea68d444a658修复）'),
    'M37': ('not_issue', 'first_annotator', 'MIPS用a3寄存器（regs[7]）标记系统调用出错，按a3返回-regs[2]，不需要IS_ERR_VALUE'),
    'M38': ('bug', 'first_annotator_nofix', '下标idx来自用户态（KVM_SET_ONE_REG的reg->id），检查上界后直接写maar[idx]，没有array_index_nospec，'
            '到终点版本仍未加（与LoongArch同类样本的标准一致）'),
    'M39': ('convention', 'first_annotator', '被noinstr/__cpuidle代码调用的sched_clock没有noinstr标注；' + NOINSTR_MIPS),
}


def main():
    if (HERE / 'labels3.json').exists():
        raise SystemExit('preserve')
    out = []
    for group, dec in (('L', L), ('M', M)):
        rows = json.loads((HERE / f'candidates_{group}.json').read_text(encoding='utf-8'))['rows']
        assert set(dec) == {r['cand'] for r in rows}, group
        for r in rows:
            d = dec[r['cand']]
            out.append({**r, 'label3': d[0], 'basis3': d[1], 'reason3': d[2], 'fix': d[3] if len(d) > 3 else None})
    note = '三类标签（criteria.md第四节），第一标注人读代码和上游提交后写定，生成提示词之前记录SHA。'
    (HERE / 'labels3.json').write_text(json.dumps({'note': note, 'rows': out}, indent=1, ensure_ascii=False) + '\n',
                                       encoding='utf-8')
    from collections import Counter
    for g in 'LM':
        print(g, Counter((r['label3'], r['basis3']) for r in out if r['cand'][0] == g))


if __name__ == '__main__':
    main()
