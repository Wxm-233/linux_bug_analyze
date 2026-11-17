"""Dev-set labels (criteria.md sections 3-4). The 121 single-function fixes keep their earlier labels
(mech_catalog_validation_20261102/labels.json), re-checked against catalog_v2.md: changed mechanisms are listed in
CHANGES with the reason; every C row gets the counterpart fields that the earlier round did not record. A350 is the
one dev commit outside the 121. Output: labels/bDEV.json, labels/dev_changes.json.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'mech_catalog_validation_20261102' / 'labels.json'

# commit -> (new mechanism or None, reason) for labels changed under catalog v2
CHANGES = {
    'c27fa53b858b': ('M10', 'X1→M10：信号返回恢复向量状态的顺序，与arm64同一约定、顺序不同'),
    '10541b374aa0': ('M10', 'X1→M10：BPF trampoline运行统计，同一约定各自实现'),
    '61119394631f': ('M10', 'X1→M10：系统调用号-1返回-ENOSYS，公共ptrace约定、RISC-V条件不同'),
    'bbb622488749': ('M10', 'X1→M10：KVM创建perf计数器须先禁用，arm64 KVM同一约定'),
    'b342166cbcf9': ('M10', 'X1→M10：脏页记录须强制页粒度，arm64 KVM同一约定'),
    '5eb6d68fe24d': ('M10', 'X1→M10：KVM_SET_GUEST_DEBUG语义，公共KVM接口各自实现'),
}

# commit -> (kind, counterpart location, state, masking mode)
CROSS = {
    'e59e5e2754bf': ('K2', 'arch/x86/mm/dump_pagetables.c（按运行时级数命名）', 'S1', '1'),
    '767423658d53': ('K2', 'arch/arm64/kernel/kexec_image.c:image_load（buf_align = MIN_KIMG_ALIGN）', 'S1', '0'),
    '749b94b08005': ('K2', 'arch/x86/kernel/module.c:module_alloc（VM_FLUSH_RESET_PERMS）', 'S1', '0'),
    '4525462dd0db': ('K1', 'init/Kconfig:CC_HAS_ASM_GOTO_OUTPUT', 'S0', '2'),
    'c27fa53b858b': ('K2', 'arch/arm64/kernel/signal.c（恢复FPSIMD/SVE状态的顺序）', 'S1', '0'),
    '10541b374aa0': ('K2', 'arch/arm64/net/bpf_jit_comp.c:invoke_bpf_prog', 'S2', '0'),
    '994af1825a2a': ('K1', 'include/linux/err.h:IS_ERR_VALUE（最后一页地址与错误码重叠）', 'S0', '2'),
    '20a759df3bba': ('K2', 'arch/arm64/net/bpf_jit_comp.c:emit_lse_atomic（带acquire-release）', 'S1', '3'),
    'c67ddf59ac44': ('K2', 'arch/arm64/mm/mmu.c（can_set_direct_map时不用块映射）', 'S1', '2'),
    'c562ba719df5': ('K2', 'arch/arm64/kernel/machine_kexec.c:machine_kexec_mask_interrupts', 'S1', '2'),
    '61119394631f': ('K2', 'arch/arm64/kernel/syscall.c:el0_svc_common（x0置-ENOSYS）', 'S1', '2'),
    '0c710050c47d': ('K1', 'arch/x86/mm/fault.c:mm_fault_error（处理VM_FAULT_SIGSEGV）', 'S1', '4'),
    'e59db0623f69': ('K2', 'arch/arm64/net/bpf_jit_comp.c:emit_lse_atomic', 'S1', '3'),
    'b3134b8c1a1c': ('K2', 'arch/arm64/kernel/jump_label.c（不取mutex）', 'S1', '0'),
    'bbb622488749': ('K2', 'arch/arm64/kvm/pmu-emul.c:kvm_pmu_create_perf_event（attr.disabled）', 'S1', '0'),
    '2d117e67f318': ('K1', 'virt/kvm/kvm_main.c:kvm_exit', 'S0', '0'),
    '453805f0a28f': ('K2', 'arch/arm64/kernel/entry-common.c（el0异常处理先开中断）', 'S1', '2'),
    '8c5fa3764fac': ('K1', 'arch/arm64/kvm/mmu.c:kvm_arch_prepare_memory_region（VM_PFNMAP判断）', 'S0', '4'),
    'b342166cbcf9': ('K2', 'arch/arm64/kvm/mmu.c:user_mem_abort（logging_active时force_pte）', 'S1', '0'),
    '6b60a128c2f4': ('K2', 'arch/arm64/kernel/patching.c（arm64同修8d09e2d569f6）', 'S2', '0'),
    'a216e24fc947': ('K2', 'arch/arm64/kvm/mmu.c（写保护覆盖整块）', 'S1', '0'),
    '5eb6d68fe24d': ('K2', 'arch/arm64/kvm/guest.c:kvm_arch_vcpu_ioctl_set_guest_debug', 'S1', '0'),
    '5fc6e7d45373': ('K2', 'arch/arm64/kernel/machine_kexec_file.c:prepare_elf_headers（排除crashk_low_res）', 'S1', '4'),
    '81bbcff0c053': ('K3', 'security/integrity/ima/ima_kexec.c（可能产生空缓冲区）', 'S0', '0'),
    'e8f3e9ba146a': ('K2', 'arch/arm64/kvm/mmu.c:kvm_arch_prepare_memory_region（按IPA上限检查）', 'S1', '0'),
}

EXTRA = {'A350': ['M4', 'C', 'K3', 'mm/ptdump.c:ptdump_check_wx', 'S2', '2', '',
                  'ptdump遍历与内存热拔并发；arm64、RISC-V、s390同样只在debugfs路径加锁，check_wx路径漏了']}


def main():
    items = {i['commit']: i for i in json.loads((HERE / 'items.json').read_text(encoding='utf-8'))}
    rows, changes = [], []
    for r in json.loads(OLD.read_text(encoding='utf-8'))['rows']:
        mech, cx, reason = r['class'], r['cross'], r['reason']
        if r['commit'] in CHANGES:
            new, why = CHANGES[r['commit']]
            changes.append({'id': items[r['commit']]['id'], 'commit': r['commit'], 'old': mech, 'new': new, 'why': why})
            mech = new
        k, loc, s, mk = CROSS.get(r['commit'], ('', '', '', '')) if cx == 'C' else ('', '', '', '')
        assert (cx == 'C') == bool(k), r['commit']
        rows.append([items[r['commit']]['id'], mech, cx, k, loc, s, mk, '', reason])
    rows += [[k] + v for k, v in EXTRA.items()]
    dev = {i['id'] for i in items.values() if i['dev'] and i['source'] == 'A'}
    assert {r[0] for r in rows} == dev, dev ^ {r[0] for r in rows}
    (HERE / 'labels' / 'bDEV.json').write_text(json.dumps(sorted(rows), ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    (HERE / 'labels' / 'dev_changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(rows), 'changes', len(changes))


if __name__ == '__main__':
    main()
