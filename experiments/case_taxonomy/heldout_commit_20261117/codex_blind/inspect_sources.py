import pathlib
import re
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent
JOBS = {
    'early': [
        (1, '0f90b88dbcd1', 'arch/x86/kernel/kvmclock.c', r'^bool kvm_check_and_clear_guest_paused', 0, 16),
        (1, '0f90b88dbcd1', 'include/asm-generic/kvm_para.h', r'^static inline bool kvm_check_and_clear_guest_paused', 0, 5),
        (3, 'd9807d60c145', 'arch/riscv/include/asm/cacheflush.h', r'flush_cache_vmap', 5, 12),
        (3, 'd9807d60c145', 'mm/sparse-vmemmap.c', r'^struct page .*__populate_section_memmap', 0, 44),
        (4, 'd94c12bd97d5', 'arch/arm64/include/asm/word-at-a-time.h', r'load_unaligned_zeropad', 6, 30),
        (5, '59f876fb9d68', 'arch/arm/include/asm/bitops.h', r'__ffs', 3, 10),
        (9, '22883973244b', 'include/linux/uaccess.h', r'^#ifndef untagged_addr', 5, 9),
        (9, '22883973244b', 'arch/x86/include/asm/uaccess_64.h', r'^static inline unsigned long __untagged_addr_remote', 2, 15),
        (10, '56ae10cf628b', 'arch/powerpc/include/asm/nohash/32/pte-8xx.h', r'^#define ptep_get ptep_get', 2, 10),
        (13, '546e42c8c6d9', 'include/linux/pgtable.h', r'^static inline pud_t pudp_huge_get_and_clear', 8, 16),
        (14, 'edf2d546bfd6', 'arch/riscv/kernel/patch.c', r'^static void patch_unmap|^static int __patch_insn_write', 2, 40),
    ],
    'access': [
        (21, 'd5dc200c3a3f', 'arch/x86/include/asm/uaccess.h', r'^ \* __get_user|^#define __get_user\(', 2, 24),
        (21, 'd5dc200c3a3f', 'arch/arm64/include/asm/uaccess.h', r'^#define __get_user\(', 8, 15),
        (21, 'd5dc200c3a3f', 'include/asm-generic/uaccess.h', r'^#define __get_user\(', 4, 25),
        (24, 'b3f78e749865', 'arch/arm/include/asm/pgtable.h', r'^static inline void set_pte_at|^extern void set_pte_at|^#define set_pte_at', 4, 27),
        (24, 'b3f78e749865', 'arch/arm/mm/mmu.c', r'^void set_pte_at', 2, 30),
        (24, 'b3f78e749865', 'arch/x86/include/asm/paravirt.h', r'^static inline void set_pte_at', 2, 15),
        (50, 'eec76ea5a721', 'include/crypto/internal/poly1305.h', r'poly1305_blocks_arch|poly1305_blocks\(', 12, 24),
        (50, 'eec76ea5a721', 'lib/crypto/arm64/poly1305-glue.c', r'^void poly1305_blocks_arch', 4, 48),
    ],
    'late': [
        (51, '2858b4027f49', 'include/linux/pgtable.h', r'pmd_is_huge', 10, 20),
        (51, '2858b4027f49', 'include/linux/huge_mm.h', r'pmd_is_huge|pmd_trans_huge_lock', 10, 20),
        (51, '2858b4027f49', 'arch/x86/include/asm/pgtable.h', r'^static inline int pmd_trans_huge', 3, 18),
        (51, '2858b4027f49', 'arch/arm64/include/asm/pgtable.h', r'^static inline int pmd_trans_huge|^#define pmd_trans_huge', 3, 18),
        (51, '2858b4027f49', 'mm/Kconfig', r'^config DEVICE_PRIVATE', 4, 18),
        (54, '2d331a6ac481', 'drivers/acpi/resource.c', r'acpi_get_override_irq', 12, 20),
        (54, '2d331a6ac481', 'arch/x86/kernel/acpi/boot.c', r'^int acpi_get_override_irq', 2, 20),
        (57, 'e5dec38ac5d0', 'drivers/irqchip/Kconfig', r'^config LOONGSON_PCH_PIC', 2, 16),
        (60, '1690eeb0cb2b', 'drivers/irqchip/Kconfig', r'^config ARM_GIC_V5', 2, 24),
    ],
    'followup': [
        (3, 'd9807d60c145', 'arch/riscv/mm/init.c', r'^int __meminit vmemmap_populate|^void __init misc_mem_init', 3, 26),
        (8, '8891b176d350', 'kernel/fork.c', r'^static struct task_struct \*dup_task_struct', 0, 33),
        (17, 'af0c3f058662', 'arch/arm64/include/asm/memory.h', r'^#define SECTION_SIZE_BITS', 3, 6),
        (21, 'd5dc200c3a3f', 'arch/arm64/include/asm/uaccess.h', r'^#define __get_user_error', 1, 20),
        (24, 'b3f78e749865', 'arch/x86/include/asm/pgtable.h', r'set_pte_at\(', 4, 20),
        (50, 'eec76ea5a721', 'include/crypto/poly1305.h', r'Context:|poly1305_blocks_arch|may_use_simd|poly1305_is_arch_optimized', 7, 17),
        (50, 'eec76ea5a721', 'lib/crypto/poly1305.c', r'poly1305_blocks_arch|may_use_simd', 10, 15),
        (54, '2d331a6ac481', 'arch/x86/kernel/acpi/boot.c', r'acpi_get_override_irq', 3, 24),
    ],
}

def run(group):
    blocks = []
    for k, commit, filename, pattern, before, after in JOBS[group]:
        data = subprocess.check_output(['git', '-C', '/root/repos/linux', '--no-pager', 'show', f'{commit}:{filename}']).decode('utf-8')
        lines = data.splitlines()
        matches = [i for i, line in enumerate(lines) if re.search(pattern, line)]
        blocks.append(f'[{k}] {commit}:{filename} pattern={pattern}')
        selected = set()
        for i in matches:
            selected.update(range(max(0, i-before), min(len(lines), i+after+1)))
        if not selected:
            blocks.append('(pattern not found; no source inference from this query)')
        last = -2
        for i in sorted(selected):
            if i != last + 1:
                blocks.append('...')
            blocks.append(f'{i+1}: {lines[i]}')
            last = i
        blocks.append('')
    evidence = '\n'.join(blocks) + '\n'
    (OUT / f'source_evidence_{group}.txt').write_text(evidence, encoding='utf-8')
    print(evidence)

run(sys.argv[1])
