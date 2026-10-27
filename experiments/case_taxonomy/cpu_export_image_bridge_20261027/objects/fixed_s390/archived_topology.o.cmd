cmd_drivers/base/topology.o := s390x-linux-gnu-gcc -Wp,-MMD,drivers/base/.topology.o.d -nostdinc -I/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include -I./arch/s390/include/generated -I/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include -I./include -I/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi -I./arch/s390/include/generated/uapi -I/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi -I./include/generated/uapi -include /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler-version.h -include /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kconfig.h -include /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler_types.h -D__KERNEL__ -fmacro-prefix-map=/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -m64 -mbackchain -msoft-float -march=z196 -mtune=z196 -Wa,-I/root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include -pipe -Wno-sign-compare -fno-asynchronous-unwind-tables -DCONFIG_AS_CFI_VAL_OFFSET=1 -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fno-stack-protector "-Wimplicit-fallthrough=5" -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fomit-frame-pointer -ftrivial-auto-var-init=zero -fno-stack-clash-protection -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -Wno-alloc-size-larger-than -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -I /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/drivers/base -I ./drivers/base    -DKBUILD_MODFILE='"drivers/base/topology"' -DKBUILD_BASENAME='"topology"' -DKBUILD_MODNAME='"topology"' -D__KBUILD_MODNAME=kmod_topology -c -o drivers/base/topology.o /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/drivers/base/topology.c 

source_drivers/base/topology.o := /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/drivers/base/topology.c

deps_drivers/base/topology.o := \
    $(wildcard include/config/SCHED_BOOK) \
    $(wildcard include/config/SCHED_DRAWER) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler_attributes.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler-gcc.h \
    $(wildcard include/config/RETPOLINE) \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/KCOV) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mm.h \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/SYSCTL) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_BITS) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_COMPAT_BITS) \
    $(wildcard include/config/SPARSEMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/MMU) \
    $(wildcard include/config/MEM_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_USES_HIGH_VMA_FLAGS) \
    $(wildcard include/config/ARCH_HAS_PKEYS) \
    $(wildcard include/config/PPC) \
    $(wildcard include/config/X86) \
    $(wildcard include/config/PARISC) \
    $(wildcard include/config/IA64) \
    $(wildcard include/config/SPARC64) \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/ARM64_MTE) \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_MINOR) \
    $(wildcard include/config/STACK_GROWSUP) \
    $(wildcard include/config/SHMEM) \
    $(wildcard include/config/TRANSPARENT_HUGEPAGE) \
    $(wildcard include/config/HUGETLB_PAGE) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/DEV_PAGEMAP_OPS) \
    $(wildcard include/config/DEVICE_PRIVATE) \
    $(wildcard include/config/PCI_P2PDMA) \
    $(wildcard include/config/NUMA_BALANCING) \
    $(wildcard include/config/KASAN_SW_TAGS) \
    $(wildcard include/config/KASAN_HW_TAGS) \
    $(wildcard include/config/MIGRATION) \
    $(wildcard include/config/HIGHMEM) \
    $(wildcard include/config/ARCH_HAS_PTE_SPECIAL) \
    $(wildcard include/config/ARCH_HAS_PTE_DEVMAP) \
    $(wildcard include/config/DEBUG_VM_RB) \
    $(wildcard include/config/PAGE_POISONING) \
    $(wildcard include/config/INIT_ON_ALLOC_DEFAULT_ON) \
    $(wildcard include/config/INIT_ON_FREE_DEFAULT_ON) \
    $(wildcard include/config/DEBUG_PAGEALLOC) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/HUGETLBFS) \
    $(wildcard include/config/MAPPING_DIRTY_HELPERS) \
    $(wildcard include/config/PRINTK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/errno.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/errno.h \
  arch/s390/include/generated/uapi/asm/errno.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/errno.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/errno-base.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bug.h \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/bug.h \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
    $(wildcard include/config/CFI_CLANG) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compiler_types.h \
  arch/s390/include/generated/asm/rwonce.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/rwonce.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/int-ll64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/int-ll64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/bitsperlong.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitsperlong.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/bitsperlong.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/posix_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stddef.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/stddef.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/posix_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/posix_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bug.h \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/MODULES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/instrumentation.h \
    $(wildcard include/config/DEBUG_ENTRY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/once_lite.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
    $(wildcard include/config/DYNAMIC_DEBUG_CORE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stdarg.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/init.h \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/STRICT_KERNEL_RWX) \
    $(wildcard include/config/STRICT_MODULE_RWX) \
    $(wildcard include/config/LTO_CLANG) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kern_levels.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stringify.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_REL_CRCS) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/linkage.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/asm-const.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/kernel.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/sysinfo.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/const.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/const.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/const.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/cache.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ratelimit_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bits.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/bits.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/build_bug.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/param.h \
  arch/s390/include/generated/uapi/asm/param.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/param.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/spinlock_types.h \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/spinlock_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rwlock_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/gfp.h \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/PM_SLEEP) \
    $(wildcard include/config/CONTIG_ALLOC) \
    $(wildcard include/config/CMA) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mmzone.h \
    $(wildcard include/config/FORCE_MAX_ZONEORDER) \
    $(wildcard include/config/MEMORY_ISOLATION) \
    $(wildcard include/config/ZSMALLOC) \
    $(wildcard include/config/SHADOW_CALL_STACK) \
    $(wildcard include/config/SWAP) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/COMPACTION) \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/PAGE_EXTENSION) \
    $(wildcard include/config/DEFERRED_STRUCT_PAGE_INIT) \
    $(wildcard include/config/HAVE_MEMORYLESS_NODES) \
    $(wildcard include/config/SPARSEMEM_EXTREME) \
    $(wildcard include/config/HAVE_ARCH_PFN_VALID) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/spinlock.h \
    $(wildcard include/config/PREEMPTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/typecheck.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/list.h \
    $(wildcard include/config/DEBUG_LIST) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/container_of.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/err.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/barrier.h \
    $(wildcard include/config/HAVE_MARCH_Z196_FEATURES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/barrier.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/preempt.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/current.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/lowcore.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/ptrace.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/ptrace.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/tpi.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/schid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/cpu.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/jump_label.h \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/atomic.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/atomic.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/atomic_ops.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/cmpxchg.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/atomic/atomic-long.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/atomic/atomic-instrumented.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/instrumented.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/thread_info.h \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/GENERIC_ENTRY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/HARDENED_USERCOPY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/limits.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/limits.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/limits.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/restart_block.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/time64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/math.h \
  arch/s390/include/generated/asm/div64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/div64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/math64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/time64.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/time.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/time_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bitops.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/bitops.h \
    $(wildcard include/config/HAVE_MARCH_Z9_109_FEATURES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/instrumented-atomic.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/instrumented-non-atomic.h \
    $(wildcard include/config/KCSAN_ASSUME_PLAIN_WRITES_ATOMIC) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/instrumented-lock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/ffz.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/find.h \
    $(wildcard include/config/GENERIC_FIND_FIRST_BIT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/hweight.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/arch_hweight.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/const_hweight.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/sched.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/le.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/byteorder.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/byteorder/big_endian.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/byteorder/big_endian.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/swab.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/swab.h \
  arch/s390/include/generated/uapi/asm/swab.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/swab.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/byteorder/generic.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/thread_info.h \
    $(wildcard include/config/KASAN) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/page.h \
    $(wildcard include/config/PGSTE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/setup.h \
    $(wildcard include/config/COMMAND_LINE_SIZE) \
    $(wildcard include/config/PFAULT) \
    $(wildcard include/config/VMCP) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/setup.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/memory_model.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pfn.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/getorder.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/irqflags.h \
    $(wildcard include/config/PROVE_LOCKING) \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/irqflags.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/percpu.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/percpu.h \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/threads.h \
    $(wildcard include/config/NR_CPUS) \
    $(wildcard include/config/BASE_SMALL) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bottom_half.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/instruction_pointer.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cpumask.h \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY_BUILD) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/FTRACE_MCOUNT_RECORD) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/align.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kstrtox.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/minmax.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
    $(wildcard include/config/HAVE_STATIC_CALL_INLINE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bitmap.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/string.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/string.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/smp_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/smp.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/sigp.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/processor.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/runtime_instr.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/runtime_instr.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/fpu/types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/sigcontext.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/fpu/internal.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/ctl_reg.h \
  arch/s390/include/generated/asm/mmiowb.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/spinlock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/alternative.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rwlock.h \
    $(wildcard include/config/PREEMPT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/spinlock_api_smp.h \
    $(wildcard include/config/INLINE_SPIN_LOCK) \
    $(wildcard include/config/INLINE_SPIN_LOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK_BH) \
    $(wildcard include/config/UNINLINE_SPIN_UNLOCK) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/GENERIC_LOCKBREAK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rwlock_api_smp.h \
    $(wildcard include/config/INLINE_READ_LOCK) \
    $(wildcard include/config/INLINE_WRITE_LOCK) \
    $(wildcard include/config/INLINE_READ_LOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_LOCK_BH) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_READ_TRYLOCK) \
    $(wildcard include/config/INLINE_WRITE_TRYLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_BH) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQRESTORE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/wait.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/wait.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/numa.h \
    $(wildcard include/config/NODES_SHIFT) \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/seqlock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mutex.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_MUTEXES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/osq_lock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/debug_locks.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ww_mutex.h \
    $(wildcard include/config/DEBUG_RT_MUTEXES) \
    $(wildcard include/config/DEBUG_WW_MUTEX_SLOWPATH) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rtmutex.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rbtree_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/nodemask.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/page-flags-layout.h \
  include/generated/bounds.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/sparsemem.h \
    $(wildcard include/config/MAX_PHYSMEM_BITS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mm_types.h \
    $(wildcard include/config/HAVE_ALIGNED_STRUCT_PAGE) \
    $(wildcard include/config/USERFAULTFD) \
    $(wildcard include/config/HAVE_ARCH_COMPAT_MMAP_BASES) \
    $(wildcard include/config/MEMBARRIER) \
    $(wildcard include/config/AIO) \
    $(wildcard include/config/MMU_NOTIFIER) \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
    $(wildcard include/config/IOMMU_SUPPORT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mm_types_task.h \
    $(wildcard include/config/SPLIT_PTLOCK_CPUS) \
    $(wildcard include/config/ARCH_ENABLE_SPLIT_PMD_PTLOCK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/auxvec.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/auxvec.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/auxvec.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rbtree.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcupdate.h \
    $(wildcard include/config/PREEMPT_RCU) \
    $(wildcard include/config/TINY_RCU) \
    $(wildcard include/config/RCU_STRICT_GRACE_PERIOD) \
    $(wildcard include/config/TASKS_RCU_GENERIC) \
    $(wildcard include/config/RCU_STALL_COMMON) \
    $(wildcard include/config/NO_HZ_FULL) \
    $(wildcard include/config/RCU_NOCB_CPU) \
    $(wildcard include/config/TASKS_RCU) \
    $(wildcard include/config/TASKS_TRACE_RCU) \
    $(wildcard include/config/TASKS_RUDE_RCU) \
    $(wildcard include/config/TREE_RCU) \
    $(wildcard include/config/DEBUG_OBJECTS_RCU_HEAD) \
    $(wildcard include/config/PROVE_RCU) \
    $(wildcard include/config/ARCH_WEAK_RELEASE_ACQUIRE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcutree.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/completion.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/swait.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/uprobes.h \
    $(wildcard include/config/UPROBES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/SYSFS) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
    $(wildcard include/config/NO_HZ_COMMON) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ktime.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/time.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/time32.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/timex.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/timex.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/timex.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/time32.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/time.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/jiffies.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/jiffies.h \
  include/generated/timeconst.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/vdso/ktime.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/timekeeping.h \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/clocksource_ids.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/mmu.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/page-flags.h \
    $(wildcard include/config/ARCH_USES_PG_UNCACHED) \
    $(wildcard include/config/MEMORY_FAILURE) \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/KSM) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/local_lock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/local_lock_internal.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/memory_hotplug.h \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/HAVE_ARCH_NODEDATA_EXTENSION) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/notifier.h \
    $(wildcard include/config/TREE_SRCU) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/SRCU) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcu_segcblist.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/srcutree.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
    $(wildcard include/config/SCHED_CLUSTER) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/arch_topology.h \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/percpu.h \
    $(wildcard include/config/NEED_PER_CPU_EMBED_FIRST_CHUNK) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/topology.h \
    $(wildcard include/config/SCHED_TOPOLOGY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/numa.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/topology.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mmap_lock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/tracepoint-defs.h \
    $(wildcard include/config/TRACEPOINTS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/static_key.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/range.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/percpu-refcount.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/bit_spinlock.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/shrinker.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/resource.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/resource.h \
  arch/s390/include/generated/uapi/asm/resource.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/resource.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/resource.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/page_ext.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stacktrace.h \
    $(wildcard include/config/STACKTRACE) \
    $(wildcard include/config/ARCH_STACKWALK) \
    $(wildcard include/config/HAVE_RELIABLE_STACKTRACE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stackdepot.h \
    $(wildcard include/config/STACKDEPOT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/page_ref.h \
    $(wildcard include/config/DEBUG_PAGE_REF) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/memremap.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ioport.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/overflow.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sizes.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_NATIVE) \
    $(wildcard include/config/SCHED_INFO) \
    $(wildcard include/config/SCHEDSTATS) \
    $(wildcard include/config/FAIR_GROUP_SCHED) \
    $(wildcard include/config/RT_GROUP_SCHED) \
    $(wildcard include/config/RT_MUTEXES) \
    $(wildcard include/config/UCLAMP_TASK) \
    $(wildcard include/config/UCLAMP_BUCKETS_COUNT) \
    $(wildcard include/config/KMAP_LOCAL) \
    $(wildcard include/config/SCHED_CORE) \
    $(wildcard include/config/CGROUP_SCHED) \
    $(wildcard include/config/BLK_DEV_IO_TRACE) \
    $(wildcard include/config/PSI) \
    $(wildcard include/config/COMPAT_BRK) \
    $(wildcard include/config/CGROUPS) \
    $(wildcard include/config/BLK_CGROUP) \
    $(wildcard include/config/PAGE_OWNER) \
    $(wildcard include/config/EVENTFD) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/ARCH_HAS_SCALED_CPUTIME) \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_GEN) \
    $(wildcard include/config/POSIX_CPUTIMERS) \
    $(wildcard include/config/POSIX_CPU_TIMERS_TASK_WORK) \
    $(wildcard include/config/KEYS) \
    $(wildcard include/config/SYSVIPC) \
    $(wildcard include/config/DETECT_HUNG_TASK) \
    $(wildcard include/config/IO_URING) \
    $(wildcard include/config/AUDIT) \
    $(wildcard include/config/AUDITSYSCALL) \
    $(wildcard include/config/UBSAN) \
    $(wildcard include/config/UBSAN_TRAP) \
    $(wildcard include/config/TASK_XACCT) \
    $(wildcard include/config/CPUSETS) \
    $(wildcard include/config/X86_CPU_RESCTRL) \
    $(wildcard include/config/FUTEX) \
    $(wildcard include/config/COMPAT) \
    $(wildcard include/config/PERF_EVENTS) \
    $(wildcard include/config/RSEQ) \
    $(wildcard include/config/TASK_DELAY_ACCT) \
    $(wildcard include/config/FAULT_INJECTION) \
    $(wildcard include/config/LATENCYTOP) \
    $(wildcard include/config/KUNIT) \
    $(wildcard include/config/FUNCTION_GRAPH_TRACER) \
    $(wildcard include/config/BCACHE) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/LIVEPATCH) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/BPF_SYSCALL) \
    $(wildcard include/config/GCC_PLUGIN_STACKLEAK) \
    $(wildcard include/config/X86_MCE) \
    $(wildcard include/config/KRETPROBES) \
    $(wildcard include/config/ARCH_HAS_PARANOID_L1D_FLUSH) \
    $(wildcard include/config/ARCH_TASK_STRUCT_ON_STACK) \
    $(wildcard include/config/DEBUG_RSEQ) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/sched.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/refcount.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sem.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/sem.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ipc.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/highuid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rhashtable-types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/ipc.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/ipcbuf.h \
  arch/s390/include/generated/uapi/asm/sembuf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/sembuf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/shm.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/shm.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/hugetlb_encode.h \
  arch/s390/include/generated/uapi/asm/shmbuf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/shmbuf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/shmparam.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/plist.h \
    $(wildcard include/config/DEBUG_PLIST) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/hrtimer_defs.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/timerqueue.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/seccomp.h \
    $(wildcard include/config/SECCOMP) \
    $(wildcard include/config/HAVE_ARCH_SECCOMP_FILTER) \
    $(wildcard include/config/SECCOMP_FILTER) \
    $(wildcard include/config/CHECKPOINT_RESTORE) \
    $(wildcard include/config/SECCOMP_CACHE_DEBUG) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/seccomp.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/latencytop.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/prio.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/signal.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/signal.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/signal.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/signal-defs.h \
  arch/s390/include/generated/uapi/asm/siginfo.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/siginfo.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/syscall_user_dispatch.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/posix-timers.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/task_work.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/rseq.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kcsan.h \
  arch/s390/include/generated/asm/kmap_size.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pgtable.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/HIGHPTE) \
    $(wildcard include/config/GUP_GET_PTE_LOW_HIGH) \
    $(wildcard include/config/HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD) \
    $(wildcard include/config/HAVE_ARCH_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_ENABLE_THP_MIGRATION) \
    $(wildcard include/config/HAVE_ARCH_HUGE_VMAP) \
    $(wildcard include/config/X86_ESPFIX64) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/pgtable.h \
    $(wildcard include/config/PROC_FS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/radix-tree.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kconfig.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/sections.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/sections.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/uv.h \
    $(wildcard include/config/PROTECTED_VIRTUALIZATION_GUEST) \
    $(wildcard include/config/KVM) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/gmap.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/pgtable_uffd.h \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kasan.h \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
    $(wildcard include/config/KASAN_INLINE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/huge_mm.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/coredump.h \
    $(wildcard include/config/CORE_DUMP_DEFAULT_ELF_HEADERS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/fs.h \
    $(wildcard include/config/READ_ONLY_THP_FOR_FS) \
    $(wildcard include/config/FS_POSIX_ACL) \
    $(wildcard include/config/CGROUP_WRITEBACK) \
    $(wildcard include/config/IMA) \
    $(wildcard include/config/FILE_LOCKING) \
    $(wildcard include/config/FSNOTIFY) \
    $(wildcard include/config/FS_ENCRYPTION) \
    $(wildcard include/config/FS_VERITY) \
    $(wildcard include/config/EPOLL) \
    $(wildcard include/config/UNICODE) \
    $(wildcard include/config/QUOTA) \
    $(wildcard include/config/FS_DAX) \
    $(wildcard include/config/BLOCK) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/wait_bit.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kdev_t.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/kdev_t.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/dcache.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rculist_bl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/list_bl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/path.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/stat.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/stat.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/stat.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/list_lru.h \
    $(wildcard include/config/MEMCG_KMEM) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/capability.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/capability.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/semaphore.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/fcntl.h \
  arch/s390/include/generated/uapi/asm/fcntl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/fcntl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/openat2.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/migrate_mode.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/percpu-rwsem.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcuwait.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/signal.h \
    $(wildcard include/config/DYNAMIC_SIGFRAME) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/jobctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/uaccess.h \
    $(wildcard include/config/SET_FS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/uaccess.h \
    $(wildcard include/config/HAVE_MARCH_Z10_FEATURES) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/extable.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/facility.h \
  arch/s390/include/generated/asm/facility-defs.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cred.h \
    $(wildcard include/config/DEBUG_CREDENTIALS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sysctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/sysctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/user.h \
    $(wildcard include/config/WATCH_QUEUE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/percpu_counter.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ratelimit.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rcu_sync.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/delayed_call.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/uuid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/uuid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/errseq.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ioprio.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/rt.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/iocontext.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/ioprio.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/fs_types.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/mount.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/fs.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/ioctl.h \
  arch/s390/include/generated/uapi/asm/ioctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/ioctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/ioctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/dqblk_xfs.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/dqblk_v1.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/dqblk_v2.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/dqblk_qtree.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/projid.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/quota.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/nfs_fs_i.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/vmstat.h \
    $(wildcard include/config/VM_EVENT_COUNTERS) \
    $(wildcard include/config/DEBUG_TLBFLUSH) \
    $(wildcard include/config/DEBUG_VM_VMACACHE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/vm_event_item.h \
    $(wildcard include/config/MEMORY_BALLOON) \
    $(wildcard include/config/BALLOON_COMPACTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cpu.h \
    $(wildcard include/config/PM_SLEEP_SMP) \
    $(wildcard include/config/PM_SLEEP_SMP_NONZERO_CPU) \
    $(wildcard include/config/HOTPLUG_SMT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/node.h \
    $(wildcard include/config/HMEM_REPORTING) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/device.h \
    $(wildcard include/config/ENERGY_MODEL) \
    $(wildcard include/config/GENERIC_MSI_IRQ_DOMAIN) \
    $(wildcard include/config/PINCTRL) \
    $(wildcard include/config/GENERIC_MSI_IRQ) \
    $(wildcard include/config/DMA_OPS) \
    $(wildcard include/config/DMA_DECLARE_COHERENT) \
    $(wildcard include/config/DMA_CMA) \
    $(wildcard include/config/SWIOTLB) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_DEVICE) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU_ALL) \
    $(wildcard include/config/DMA_OPS_BYPASS) \
    $(wildcard include/config/OF) \
    $(wildcard include/config/DEVTMPFS) \
    $(wildcard include/config/SYSFS_DEPRECATED) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/dev_printk.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/energy_model.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sysfs.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/idr.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kobject_ns.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kref.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/cpufreq.h \
    $(wildcard include/config/CPU_FREQ) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/topology.h \
    $(wildcard include/config/SCHED_DEBUG) \
    $(wildcard include/config/SCHED_MC) \
    $(wildcard include/config/CPU_FREQ_GOV_SCHEDUTIL) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/idle.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/sd_flags.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/klist.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pm.h \
    $(wildcard include/config/VT_CONSOLE_SLEEP) \
    $(wildcard include/config/PM) \
    $(wildcard include/config/PM_CLK) \
    $(wildcard include/config/PM_GENERIC_DOMAINS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/device/bus.h \
    $(wildcard include/config/ACPI) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/device/class.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/device/driver.h \
  arch/s390/include/generated/asm/device.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/device.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/pm_wakeup.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cpuhotplug.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/module.h \
    $(wildcard include/config/MODULES_TREE_LOOKUP) \
    $(wildcard include/config/STACKTRACE_BUILD_ID) \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/KALLSYMS) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/DEBUG_INFO_BTF_MODULES) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/MODULE_UNLOAD) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/buildid.h \
    $(wildcard include/config/CRASH_CORE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/kmod.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/umh.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/elf.h \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/elf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/compat.h \
    $(wildcard include/config/ARCH_HAS_SYSCALL_WRAPPER) \
    $(wildcard include/config/X86_X32_ABI) \
    $(wildcard include/config/COMPAT_OLD_SIGACTION) \
    $(wildcard include/config/ODD_RT_SIGACTION) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/socket.h \
  arch/s390/include/generated/uapi/asm/socket.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/socket.h \
  arch/s390/include/generated/uapi/asm/sockios.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/asm-generic/sockios.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/sockios.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/uio.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
    $(wildcard include/config/ARCH_HAS_COPY_MC) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/uio.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/socket.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/if.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/libc-compat.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/hdlc/ioctl.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/aio_abi.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/unistd.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/unistd.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/uapi/asm/unistd.h \
  arch/s390/include/generated/uapi/asm/unistd_64.h \
  arch/s390/include/generated/asm/unistd_nr.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/compat.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/task_stack.h \
    $(wildcard include/config/DEBUG_STACK_USAGE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/magic.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/compat.h \
    $(wildcard include/config/COMPAT_FOR_U64_ALIGNMENT) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/syscall_wrapper.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/syscall.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/audit.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/elf-em.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/user.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sched/mm.h \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/mmu_context.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/pgalloc.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/tlbflush.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/mm_hooks.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/mmu_context.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/uapi/linux/elf.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/rbtree_latch.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/error-injection.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/error-injection.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/cfi.h \
    $(wildcard include/config/CFI_CLANG_SHADOW) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/module.h \
    $(wildcard include/config/FUNCTION_TRACER) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
    $(wildcard include/config/MODULES_USE_ELF_REL) \
    $(wildcard include/config/MODULES_USE_ELF_RELA) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/hardirq.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/context_tracking_state.h \
    $(wildcard include/config/CONTEXT_TRACKING) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/ftrace_irq.h \
    $(wildcard include/config/HWLAT_TRACER) \
    $(wildcard include/config/OSNOISE_TRACER) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/include/linux/vtime.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING) \
    $(wildcard include/config/IRQ_TIME_ACCOUNTING) \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/vtime.h \
  /root/.cache/linux-bug-analyze/die-contract-20261013/fixed/linux/arch/s390/include/asm/hardirq.h \

drivers/base/topology.o: $(deps_drivers/base/topology.o)

$(deps_drivers/base/topology.o):
