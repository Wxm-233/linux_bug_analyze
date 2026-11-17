"""Strategy-derived fixes D1-D8 (criteria.md section 1), applied one by one in a temporary detached worktree of the
kernel repository at df2908090cda; each fix is committed (no branch) and written to patches/Dn.patch. Every edit is
an exact replacement that must match once. WSL (git); no model.
Usage: python3 make_patches.py   Output: patches/D1..D8.patch, patches/commits.json."""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO, END, WT = '/root/repos/linux', 'df2908090cda', '/root/fixdemo_wt'
GITC = ['-c', 'user.name=fixdemo', '-c', 'user.email=fixdemo@localhost']

NOSPEC = '#include <linux/nospec.h>\n'
FIXES = {
    'D1': [  # M2: finish porting arm64 49c87f76 -- drop the !pte_napot() gates
        ('arch/riscv/mm/hugetlbpage.c',
         '\tsize_t pgsize;\n\tpte_t orig_pte = ptep_get(ptep);\n\tint pte_num;\n\n\tif (!pte_napot(orig_pte))\n'
         '\t\treturn ptep_get_and_clear(mm, addr, ptep);\n\n\tpte_num = num_contig_ptes_from_size(sz, &pgsize);',
         '\tsize_t pgsize;\n\tint pte_num;\n\n\tpte_num = num_contig_ptes_from_size(sz, &pgsize);'),
        ('arch/riscv/mm/hugetlbpage.c',
         '\tsize_t pgsize;\n\tpte_t pte = ptep_get(ptep);\n\tint i, pte_num;\n\n\tif (!pte_napot(pte)) {\n'
         '\t\tpte_clear(mm, addr, ptep);\n\t\treturn;\n\t}\n\n\tpte_num = num_contig_ptes_from_size(sz, &pgsize);',
         '\tsize_t pgsize;\n\tint i, pte_num;\n\n\tpte_num = num_contig_ptes_from_size(sz, &pgsize);'),
    ],
    'D2': [  # M5: do not sleep with IRQs off -- disable them only after the other harts are down
        ('arch/riscv/kernel/machine_kexec.c',
         '\t/*\n\t * No more interrupts on this hart\n\t * until we are back up.\n\t */\n\tlocal_irq_disable();\n\n'
         '#if defined(CONFIG_HOTPLUG_CPU)\n\tsmp_shutdown_nonboot_cpus(smp_processor_id());\n#endif\n}',
         '#if defined(CONFIG_HOTPLUG_CPU)\n\tsmp_shutdown_nonboot_cpus(smp_processor_id());\n#endif\n\n'
         '\t/*\n\t * No more interrupts on this hart until we are back up. Disable them\n'
         '\t * only after the other harts are down: smp_shutdown_nonboot_cpus()\n\t * may sleep.\n\t */\n'
         '\tlocal_irq_disable();\n}'),
    ],
    'D3': [  # M8: follow arm64 d0bab0c39e32 -- count the other online CPUs
        ('arch/riscv/kernel/smp.c',
         '#ifdef CONFIG_KEXEC_CORE\n/*\n * The number of CPUs online, not counting this CPU (which may not be\n'
         ' * fully online and so not counted in num_online_cpus()).\n */\n'
         'static inline unsigned int num_other_online_cpus(void)\n{\n'
         '\tunsigned int this_cpu_online = cpu_online(smp_processor_id());\n\n'
         '\treturn num_online_cpus() - this_cpu_online;\n}\n\n',
         '#ifdef CONFIG_KEXEC_CORE\n'),
        ('arch/riscv/kernel/smp.c', 'void smp_send_stop(void)\n{',
         '/*\n * The number of CPUs online, not counting this CPU (which may not be\n'
         ' * fully online and so not counted in num_online_cpus()).\n */\n'
         'static inline unsigned int num_other_online_cpus(void)\n{\n'
         '\tunsigned int this_cpu_online = cpu_online(smp_processor_id());\n\n'
         '\treturn num_online_cpus() - this_cpu_online;\n}\n\nvoid smp_send_stop(void)\n{'),
        ('arch/riscv/kernel/smp.c', '\tif (num_online_cpus() > 1) {\n\t\tcpumask_t mask;',
         '\tif (num_other_online_cpus()) {\n\t\tcpumask_t mask;'),
        ('arch/riscv/kernel/smp.c', '\twhile (num_online_cpus() > 1 && timeout--)',
         '\twhile (num_other_online_cpus() && timeout--)'),
        ('arch/riscv/kernel/smp.c', '\tif (num_online_cpus() > 1)\n\t\tpr_warn("SMP: failed to stop secondary CPUs',
         '\tif (num_other_online_cpus())\n\t\tpr_warn("SMP: failed to stop secondary CPUs'),
    ],
    'D4': [  # M8: follow arm64 df6556adf27b -- age the whole range, drop the WARN_ON
        ('arch/riscv/include/asm/kvm_gstage.h',
         'bool kvm_riscv_gstage_wp_range(struct kvm_gstage *gstage, gpa_t start, gpa_t end);\n',
         'bool kvm_riscv_gstage_wp_range(struct kvm_gstage *gstage, gpa_t start, gpa_t end);\n\n'
         'bool kvm_riscv_gstage_test_young_range(struct kvm_gstage *gstage, gpa_t start, gpa_t end,\n'
         '\t\t\t\t       bool mkold);\n'),
        ('arch/riscv/kvm/gstage.c', '\treturn flush;\n}\n\nstatic inline void clear_huge_mask(',
         '\treturn flush;\n}\n\n'
         '/*\n * Test, and clear if @mkold, the accessed bit of every leaf PTE that maps\n'
         ' * [@start, @end); the range need not be exactly one page or block.\n */\n'
         'bool kvm_riscv_gstage_test_young_range(struct kvm_gstage *gstage, gpa_t start, gpa_t end,\n'
         '\t\t\t\t       bool mkold)\n{\n\tint ret;\n\tpte_t *ptep;\n\tu32 ptep_level;\n\tbool found_leaf;\n'
         '\tgpa_t addr = start;\n\tunsigned long page_size;\n\tbool young = false;\n\n'
         '\twhile (addr < end) {\n'
         '\t\tfound_leaf = kvm_riscv_gstage_get_leaf(gstage, addr, &ptep, &ptep_level);\n'
         '\t\tret = gstage_level_to_page_size(gstage, ptep_level, &page_size);\n\t\tif (ret)\n\t\t\tbreak;\n\n'
         '\t\tif (found_leaf) {\n\t\t\tif (mkold)\n\t\t\t\tyoung |= ptep_test_and_clear_young(NULL, 0, ptep);\n'
         '\t\t\telse\n\t\t\t\tyoung |= pte_young(ptep_get(ptep));\n\t\t}\n'
         '\t\taddr = ALIGN(addr + 1, page_size);\n\t}\n\n\treturn young;\n}\n\nstatic inline void clear_huge_mask('),
        ('arch/riscv/kvm/mmu.c',
         'bool kvm_age_gfn(struct kvm *kvm, struct kvm_gfn_range *range)\n{\n\tpte_t *ptep;\n\tu32 ptep_level = 0;\n'
         '\tu64 size = (range->end - range->start) << PAGE_SHIFT;\n\tstruct kvm_gstage gstage;\n\n'
         '\tif (!kvm->arch.pgd)\n\t\treturn false;\n\n'
         '\tWARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);\n\n'
         '\tkvm_riscv_gstage_init(&gstage, kvm);\n'
         '\tif (!kvm_riscv_gstage_get_leaf(&gstage, range->start << PAGE_SHIFT,\n'
         '\t\t\t\t       &ptep, &ptep_level))\n\t\treturn false;\n\n'
         '\treturn ptep_test_and_clear_young(NULL, 0, ptep);\n}',
         'bool kvm_age_gfn(struct kvm *kvm, struct kvm_gfn_range *range)\n{\n\tstruct kvm_gstage gstage;\n\n'
         '\tif (!kvm->arch.pgd)\n\t\treturn false;\n\n\tkvm_riscv_gstage_init(&gstage, kvm);\n'
         '\treturn kvm_riscv_gstage_test_young_range(&gstage, range->start << PAGE_SHIFT,\n'
         '\t\t\t\t\t\t range->end << PAGE_SHIFT, true);\n}'),
        ('arch/riscv/kvm/mmu.c',
         'bool kvm_test_age_gfn(struct kvm *kvm, struct kvm_gfn_range *range)\n{\n\tpte_t *ptep;\n\tu32 ptep_level = 0;\n'
         '\tu64 size = (range->end - range->start) << PAGE_SHIFT;\n\tstruct kvm_gstage gstage;\n\n'
         '\tif (!kvm->arch.pgd)\n\t\treturn false;\n\n'
         '\tWARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);\n\n'
         '\tkvm_riscv_gstage_init(&gstage, kvm);\n'
         '\tif (!kvm_riscv_gstage_get_leaf(&gstage, range->start << PAGE_SHIFT,\n'
         '\t\t\t\t       &ptep, &ptep_level))\n\t\treturn false;\n\n'
         '\treturn pte_young(ptep_get(ptep));\n}',
         'bool kvm_test_age_gfn(struct kvm *kvm, struct kvm_gfn_range *range)\n{\n\tstruct kvm_gstage gstage;\n\n'
         '\tif (!kvm->arch.pgd)\n\t\treturn false;\n\n\tkvm_riscv_gstage_init(&gstage, kvm);\n'
         '\treturn kvm_riscv_gstage_test_young_range(&gstage, range->start << PAGE_SHIFT,\n'
         '\t\t\t\t\t\t range->end << PAGE_SHIFT, false);\n}'),
    ],
    'D5': [  # M7: clamp the guest-controlled firmware event code
        ('arch/riscv/kvm/vcpu_pmu.c', '\t\t\tkvpmu->fw_event[event_code].started = true;',
         '\t\t\tkvpmu->fw_event[array_index_nospec(event_code, SBI_PMU_FW_MAX)].started = true;'),
    ],
    'D6': [  # M7: clamp the guest- or user-controlled indices in LoongArch KVM
        ('arch/loongarch/kvm/vcpu.c', '\tif (val >= KVM_MAX_PHYID)\n\t\treturn -EINVAL;\n',
         '\tif (val >= KVM_MAX_PHYID)\n\t\treturn -EINVAL;\n\tval = array_index_nospec(val, KVM_MAX_PHYID);\n'),
        ('arch/loongarch/kvm/vcpu.c', '\tif (cpuid >= KVM_MAX_PHYID)\n\t\treturn NULL;\n\n\tmap = kvm->arch.phyid_map;',
         '\tif (cpuid >= KVM_MAX_PHYID)\n\t\treturn NULL;\n\n\tcpuid = array_index_nospec(cpuid, KVM_MAX_PHYID);\n'
         '\tmap = kvm->arch.phyid_map;'),
        ('arch/loongarch/kvm/main.c', '\tif (csr < CSR_MAX_NUMS)\n\t\treturn gcsr_flag[csr];',
         '\tif (csr < CSR_MAX_NUMS)\n\t\treturn gcsr_flag[array_index_nospec(csr, CSR_MAX_NUMS)];'),
    ],
    'D7': [  # M10/M8: follow LoongArch ea68d444a658 -- initialise static keys before the early params
        ('arch/mips/kernel/setup.c', '\t*cmdline_p = command_line;\n\n\tparse_early_param();',
         '\t*cmdline_p = command_line;\n\n\tjump_label_init(); /* Initialise the static keys for early params */\n'
         '\tparse_early_param();'),
    ],
    'D8': [  # M7: clamp the user-controlled MAAR index, in both one_reg accessors
        ('arch/mips/kvm/vz.c', '\t\t*v = vcpu->arch.maar[idx];',
         '\t\t*v = vcpu->arch.maar[array_index_nospec(idx, ARRAY_SIZE(vcpu->arch.maar))];'),
        ('arch/mips/kvm/vz.c', '\t\tvcpu->arch.maar[idx] = mips_process_maar(dmtc_op, v);',
         '\t\tvcpu->arch.maar[array_index_nospec(idx, ARRAY_SIZE(vcpu->arch.maar))] =\n'
         '\t\t\tmips_process_maar(dmtc_op, v);'),
    ],
}
INCLUDES = {  # nospec.h where the file does not include it yet: insert after this anchor
    'arch/loongarch/kvm/vcpu.c': '#include <linux/kvm_host.h>\n',
    'arch/loongarch/kvm/main.c': '#include <linux/kvm_host.h>\n',
    'arch/mips/kvm/vz.c': '#include <linux/module.h>\n',
}


def git(*a, cwd=WT):
    return subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def edit(path, old, new):
    p = Path(WT) / path
    t = p.read_text()
    assert t.count(old) == 1, (path, old[:60], t.count(old))
    p.write_text(t.replace(old, new))


def main():
    if (HERE / 'patches').exists():
        raise SystemExit('preserve')
    (HERE / 'patches').mkdir()
    git('worktree', 'add', '--detach', WT, END, cwd=REPO)
    commits = {}
    for name, edits in FIXES.items():
        for path, old, new in edits:
            edit(path, old, new)
        for path, anchor in INCLUDES.items():
            if any(e[0] == path for e in edits):
                t = (Path(WT) / path).read_text()
                if NOSPEC not in t:
                    edit(path, anchor, anchor + NOSPEC)
        diff = git('diff')
        (HERE / 'patches' / f'{name}.patch').write_text(diff)
        git(*GITC, 'commit', '-qam', f'fixdemo {name}')
        commits[name] = git('rev-parse', 'HEAD').strip()
        print(name, commits[name][:12], diff.count('\n+') - diff.count('\n+++'), 'added lines')
    (HERE / 'patches' / 'commits.json').write_text(json.dumps({'base': END, **commits}, indent=1) + '\n')


if __name__ == '__main__':
    main()
