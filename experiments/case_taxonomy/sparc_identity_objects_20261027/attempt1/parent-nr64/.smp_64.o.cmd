savedcmd_arch/sparc/kernel/smp_64.o := sparc64-linux-gnu-gcc -Wp,-MMD,arch/sparc/kernel/.smp_64.o.d -nostdinc -I/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include -I./arch/sparc/include/generated -I/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include -I./include -I/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi -I./arch/sparc/include/generated/uapi -I/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi -I./include/generated/uapi -include /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler-version.h -include /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kconfig.h -include /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler_types.h -D__KERNEL__ -fmacro-prefix-map=/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/= -std=gnu11 -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -m64 -pipe -mno-fpu -mcpu=ultrasparc -mcmodel=medlow -ffixed-g4 -ffixed-g5 -fcall-used-g7 -Wno-sign-compare -Wa,--undeclared-regs -mtune=ultrasparc3 -fno-delete-null-pointer-checks -O2 -fno-allow-store-data-races -fno-stack-protector -fomit-frame-pointer -ftrivial-auto-var-init=zero -fno-stack-clash-protection -fstrict-flex-arrays=3 -fno-strict-overflow -fno-stack-check -fconserve-stack -Wall -Wundef -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Werror=strict-prototypes -Wno-format-security -Wno-trigraphs -Wno-frame-address -Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes -Wframe-larger-than=2048 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-dangling-pointer -Wvla -Wno-pointer-sign -Wcast-function-type -Wno-stringop-overflow -Wno-array-bounds -Wno-alloc-size-larger-than -Wimplicit-fallthrough=5 -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wenum-conversion -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-restrict -Wno-packed-not-aligned -Wno-format-overflow -Wno-format-truncation -Wno-stringop-truncation -Wno-missing-field-initializers -Wno-type-limits -Wno-shift-negative-value -Wno-maybe-uninitialized -Wno-sign-compare -I /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/kernel -I ./arch/sparc/kernel    -DKBUILD_MODFILE='"arch/sparc/kernel/smp_64"' -DKBUILD_BASENAME='"smp_64"' -DKBUILD_MODNAME='"smp_64"' -D__KBUILD_MODNAME=kmod_smp_64 -c -o arch/sparc/kernel/smp_64.o /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/kernel/smp_64.c  

source_arch/sparc/kernel/smp_64.o := /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/kernel/smp_64.c

deps_arch/sparc/kernel/smp_64.o := \
    $(wildcard include/config/SUN_LDOMS) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/KGDB) \
    $(wildcard include/config/DEBUG_DCFLUSH) \
    $(wildcard include/config/SERIAL_SUNHV) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler_types.h \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/PAHOLE_HAS_BTF_TAG) \
    $(wildcard include/config/FUNCTION_ALIGNMENT) \
    $(wildcard include/config/CC_HAS_SANE_FUNCTION_ALIGNMENT) \
    $(wildcard include/config/X86_64) \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/UBSAN_SIGNED_WRAP) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler_attributes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler-gcc.h \
    $(wildcard include/config/MITIGATION_RETPOLINE) \
    $(wildcard include/config/GCC_ASM_GOTO_OUTPUT_WORKAROUND) \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/SHADOW_CALL_STACK) \
    $(wildcard include/config/KCOV) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/64BIT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/OBJTOOL) \
  arch/sparc/include/generated/asm/rwonce.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/rwonce.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/types.h \
  arch/sparc/include/generated/uapi/asm/types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/int-ll64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/int-ll64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/bitsperlong.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitsperlong.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/bitsperlong.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/posix_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stddef.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/stddef.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/posix_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/posix_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_WEAK_MEMORY) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stringify.h \
  arch/sparc/include/generated/asm/linkage.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/linkage.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY_BUILD) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_CALL) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_KEY) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/MMU) \
    $(wildcard include/config/PROVE_LOCKING) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/FTRACE_MCOUNT_RECORD) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stdarg.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/align.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/const.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/const.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/const.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/array_size.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/limits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/limits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/limits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/container_of.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/build_bug.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bitops.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/bits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/bits.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/typecheck.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/kernel.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/sysinfo.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/generic-non-atomic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/barrier.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/barrier_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/barrier.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/bitops.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/bitops_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/byteorder.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/byteorder/big_endian.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/byteorder/big_endian.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/swab.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/swab.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/swab.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/asi.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/byteorder/generic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/non-atomic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/non-instrumented-non-atomic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/fls64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/ffz.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/sched.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/const_hweight.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/lock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/atomic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/atomic.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/atomic_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cmpxchg.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cmpxchg_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/cmpxchg-local.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqflags.h \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqflags_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cleanup.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/irqflags.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/irqflags_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pil.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/percpu.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/percpu_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/trap_block.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/threads.h \
    $(wildcard include/config/NR_CPUS) \
    $(wildcard include/config/BASE_SMALL) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/hypervisor.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/scratchpad.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/percpu.h \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/atomic/atomic-long.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/atomic/atomic-instrumented.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/instrumented.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kmsan-checks.h \
    $(wildcard include/config/KMSAN) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/instrumented-lock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/le.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hex.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kstrtox.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/math.h \
  arch/sparc/include/generated/asm/div64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/div64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/minmax.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/PRINTK) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
    $(wildcard include/config/DYNAMIC_DEBUG_CORE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/init.h \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/LTO_CLANG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kern_levels.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ratelimit_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/param.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/param.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/param.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/spinlock_types.h \
    $(wildcard include/config/QUEUED_SPINLOCKS) \
    $(wildcard include/config/QUEUED_RWLOCKS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/qspinlock_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/qrwlock_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/once_lite.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sprintf.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
    $(wildcard include/config/HAVE_STATIC_CALL_INLINE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/instruction_pointer.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/wordpart.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/mm.h \
    $(wildcard include/config/MMU_LAZY_TLB_REFCOUNT) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/MEMBARRIER) \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_NATIVE) \
    $(wildcard include/config/SCHED_INFO) \
    $(wildcard include/config/SCHEDSTATS) \
    $(wildcard include/config/SCHED_CORE) \
    $(wildcard include/config/FAIR_GROUP_SCHED) \
    $(wildcard include/config/RT_GROUP_SCHED) \
    $(wildcard include/config/RT_MUTEXES) \
    $(wildcard include/config/UCLAMP_TASK) \
    $(wildcard include/config/UCLAMP_BUCKETS_COUNT) \
    $(wildcard include/config/KMAP_LOCAL) \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/CGROUP_SCHED) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
    $(wildcard include/config/BLK_DEV_IO_TRACE) \
    $(wildcard include/config/PREEMPT_RCU) \
    $(wildcard include/config/TASKS_RCU) \
    $(wildcard include/config/TASKS_TRACE_RCU) \
    $(wildcard include/config/LRU_GEN) \
    $(wildcard include/config/COMPAT_BRK) \
    $(wildcard include/config/CGROUPS) \
    $(wildcard include/config/BLK_CGROUP) \
    $(wildcard include/config/PSI) \
    $(wildcard include/config/PAGE_OWNER) \
    $(wildcard include/config/EVENTFD) \
    $(wildcard include/config/ARCH_HAS_CPU_PASID) \
    $(wildcard include/config/CPU_SUP_INTEL) \
    $(wildcard include/config/TASK_DELAY_ACCT) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/ARCH_HAS_SCALED_CPUTIME) \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_GEN) \
    $(wildcard include/config/NO_HZ_FULL) \
    $(wildcard include/config/POSIX_CPUTIMERS) \
    $(wildcard include/config/POSIX_CPU_TIMERS_TASK_WORK) \
    $(wildcard include/config/KEYS) \
    $(wildcard include/config/SYSVIPC) \
    $(wildcard include/config/DETECT_HUNG_TASK) \
    $(wildcard include/config/IO_URING) \
    $(wildcard include/config/AUDIT) \
    $(wildcard include/config/AUDITSYSCALL) \
    $(wildcard include/config/DEBUG_MUTEXES) \
    $(wildcard include/config/UBSAN) \
    $(wildcard include/config/UBSAN_TRAP) \
    $(wildcard include/config/COMPACTION) \
    $(wildcard include/config/TASK_XACCT) \
    $(wildcard include/config/CPUSETS) \
    $(wildcard include/config/X86_CPU_RESCTRL) \
    $(wildcard include/config/FUTEX) \
    $(wildcard include/config/COMPAT) \
    $(wildcard include/config/PERF_EVENTS) \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/NUMA_BALANCING) \
    $(wildcard include/config/RSEQ) \
    $(wildcard include/config/SCHED_MM_CID) \
    $(wildcard include/config/FAULT_INJECTION) \
    $(wildcard include/config/LATENCYTOP) \
    $(wildcard include/config/KUNIT) \
    $(wildcard include/config/FUNCTION_GRAPH_TRACER) \
    $(wildcard include/config/MEMCG_KMEM) \
    $(wildcard include/config/UPROBES) \
    $(wildcard include/config/BCACHE) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/LIVEPATCH) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/BPF_SYSCALL) \
    $(wildcard include/config/GCC_PLUGIN_STACKLEAK) \
    $(wildcard include/config/X86_MCE) \
    $(wildcard include/config/KRETPROBES) \
    $(wildcard include/config/RETHOOK) \
    $(wildcard include/config/ARCH_HAS_PARANOID_L1D_FLUSH) \
    $(wildcard include/config/RV) \
    $(wildcard include/config/USER_EVENTS) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/PREEMPT_NONE) \
    $(wildcard include/config/PREEMPT_VOLUNTARY) \
    $(wildcard include/config/PREEMPT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/sched.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/current.h \
    $(wildcard include/config/SPARC64) \
    $(wildcard include/config/SPARC32) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/thread_info.h \
    $(wildcard include/config/GENERIC_ENTRY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/HARDENED_USERCOPY) \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/SH) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bug.h \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/bug.h \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/instrumentation.h \
    $(wildcard include/config/NOINSTR_VALIDATION) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/restart_block.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/errno.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/errno.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/errno.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/errno-base.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/thread_info.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/thread_info_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/page.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/page_64.h \
    $(wildcard include/config/PAGE_SHIFT) \
    $(wildcard include/config/HUGETLB_PAGE) \
    $(wildcard include/config/TRANSPARENT_HUGEPAGE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pfn.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/getorder.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/ptrace.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/ptrace.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/pstate.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/switch_to.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/switch_to_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/visasm.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/processor.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/processor_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/fpumacro.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
  arch/sparc/include/generated/asm/preempt.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/preempt.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cpumask.h \
    $(wildcard include/config/FORCE_NR_CPUS) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bitmap.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/find.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/args.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/err.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/overflow.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/string.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/string.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/string_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bitmap-str.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/gfp_types.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/numa.h \
    $(wildcard include/config/NODES_SHIFT) \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
    $(wildcard include/config/HAVE_ARCH_NODE_DEV_GROUP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/sparsemem.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cache.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/smp_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pid_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sem_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/shm.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/shmparam.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/shmparam_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/spitfire.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kmsan_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mutex_types.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/osq_lock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/spinlock_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rwlock_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/plist_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hrtimer_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timerqueue_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rbtree_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timer_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/seccomp_types.h \
    $(wildcard include/config/SECCOMP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/nodemask_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/refcount_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/resource.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/resource.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/time_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/resource.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/resource.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/resource.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/latencytop.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/prio.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/signal.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/signal.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/personality.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/personality.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/signal.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/sigcontext.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/sigcontext.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/signal-defs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/siginfo.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/siginfo.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/syscall_user_dispatch_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mm_types_task.h \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
    $(wildcard include/config/SPLIT_PTLOCK_CPUS) \
    $(wildcard include/config/ARCH_ENABLE_SPLIT_PMD_PTLOCK) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/posix-timers_types.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/rseq.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/seqlock_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kcsan.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rv.h \
    $(wildcard include/config/RV_REACTORS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/livepatch_sched.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/jump_label.h \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/uidgid_types.h \
  arch/sparc/include/generated/asm/kmap_size.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/spinlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bottom_half.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/list.h \
    $(wildcard include/config/LIST_HARDENED) \
    $(wildcard include/config/DEBUG_LIST) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/smp.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/smp_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/starfire.h \
  arch/sparc/include/generated/asm/mmiowb.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/spinlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/spinlock_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/qspinlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/qspinlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/qrwlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/qrwlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rwlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/spinlock_api_smp.h \
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
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rwlock_api_smp.h \
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
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mm_types.h \
    $(wildcard include/config/HAVE_ALIGNED_STRUCT_PAGE) \
    $(wildcard include/config/USERFAULTFD) \
    $(wildcard include/config/ANON_VMA_NAME) \
    $(wildcard include/config/PER_VMA_LOCK) \
    $(wildcard include/config/SWAP) \
    $(wildcard include/config/HAVE_ARCH_COMPAT_MMAP_BASES) \
    $(wildcard include/config/AIO) \
    $(wildcard include/config/MMU_NOTIFIER) \
    $(wildcard include/config/IOMMU_MM_DATA) \
    $(wildcard include/config/KSM) \
    $(wildcard include/config/LRU_GEN_WALKS_MMU) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/auxvec.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/auxvec.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/auxvec.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kref.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/refcount.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rbtree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcupdate.h \
    $(wildcard include/config/TINY_RCU) \
    $(wildcard include/config/RCU_STRICT_GRACE_PERIOD) \
    $(wildcard include/config/RCU_LAZY) \
    $(wildcard include/config/TASKS_RCU_GENERIC) \
    $(wildcard include/config/RCU_STALL_COMMON) \
    $(wildcard include/config/KVM_XFER_TO_GUEST_WORK) \
    $(wildcard include/config/RCU_NOCB_CPU) \
    $(wildcard include/config/TASKS_RUDE_RCU) \
    $(wildcard include/config/TREE_RCU) \
    $(wildcard include/config/DEBUG_OBJECTS_RCU_HEAD) \
    $(wildcard include/config/PROVE_RCU) \
    $(wildcard include/config/ARCH_WEAK_RELEASE_ACQUIRE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/context_tracking_irq.h \
    $(wildcard include/config/CONTEXT_TRACKING_IDLE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcutree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/maple_tree.h \
    $(wildcard include/config/MAPLE_RCU_DISABLED) \
    $(wildcard include/config/DEBUG_MAPLE_TREE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/completion.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/swait.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/wait.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/uprobes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/uprobes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page-flags-layout.h \
  include/generated/bounds.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/SYSFS) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ktime.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/jiffies.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/math64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/time.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/time64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/time64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/time.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/time32.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timex.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/timex.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/timex.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/timex_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/timer.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/timer_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/time32.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/time.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/jiffies.h \
  include/generated/timeconst.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/vdso/ktime.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timekeeping.h \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/clocksource_ids.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/workqueue_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/seqlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mutex.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/debug_locks.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/percpu_counter.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/percpu.h \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/RANDOM_KMALLOC_CACHES) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VM_IRQSOFF) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mmu.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mmu_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/gfp.h \
    $(wildcard include/config/HIGHMEM) \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/CONTIG_ALLOC) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mmzone.h \
    $(wildcard include/config/ARCH_FORCE_MAX_ORDER) \
    $(wildcard include/config/CMA) \
    $(wildcard include/config/MEMORY_ISOLATION) \
    $(wildcard include/config/ZSMALLOC) \
    $(wildcard include/config/UNACCEPTED_MEMORY) \
    $(wildcard include/config/LRU_GEN_STATS) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/MEMORY_FAILURE) \
    $(wildcard include/config/PAGE_EXTENSION) \
    $(wildcard include/config/DEFERRED_STRUCT_PAGE_INIT) \
    $(wildcard include/config/HAVE_MEMORYLESS_NODES) \
    $(wildcard include/config/SPARSEMEM_EXTREME) \
    $(wildcard include/config/HAVE_ARCH_PFN_VALID) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/list_nulls.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/nodemask.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/random.h \
    $(wildcard include/config/VMGENID) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/random.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/ioctl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/ioctl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqnr.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/irqnr.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/prandom.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/once.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page-flags.h \
    $(wildcard include/config/ARCH_USES_PG_UNCACHED) \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_X) \
    $(wildcard include/config/HUGETLB_PAGE_OPTIMIZE_VMEMMAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/local_lock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/local_lock_internal.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/zswap.h \
    $(wildcard include/config/ZSWAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/memory_hotplug.h \
    $(wildcard include/config/HAVE_ARCH_NODEDATA_EXTENSION) \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/notifier.h \
    $(wildcard include/config/TREE_SRCU) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/NEED_SRCU_NMI_SAFE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcu_segcblist.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/srcutree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mmzone.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/arch_topology.h \
    $(wildcard include/config/ACPI_CPPC_LIB) \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/topology.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/topology_64.h \
    $(wildcard include/config/PCI) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cpudata.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cpudata_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
    $(wildcard include/config/ARCH_HAS_PREPARE_SYNC_CORE_CMD) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/hotplug.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mm.h \
    $(wildcard include/config/SYSCTL) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_BITS) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_COMPAT_BITS) \
    $(wildcard include/config/MEM_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_USES_HIGH_VMA_FLAGS) \
    $(wildcard include/config/ARCH_HAS_PKEYS) \
    $(wildcard include/config/PPC) \
    $(wildcard include/config/X86_USER_SHADOW_STACK) \
    $(wildcard include/config/X86) \
    $(wildcard include/config/PARISC) \
    $(wildcard include/config/ARM64_MTE) \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_MINOR) \
    $(wildcard include/config/STACK_GROWSUP) \
    $(wildcard include/config/SHMEM) \
    $(wildcard include/config/FS_DAX) \
    $(wildcard include/config/MIGRATION) \
    $(wildcard include/config/ARCH_HAS_GIGANTIC_PAGE) \
    $(wildcard include/config/ARCH_HAS_PTE_SPECIAL) \
    $(wildcard include/config/ARCH_HAS_PTE_DEVMAP) \
    $(wildcard include/config/DEBUG_VM_RB) \
    $(wildcard include/config/PAGE_POISONING) \
    $(wildcard include/config/INIT_ON_ALLOC_DEFAULT_ON) \
    $(wildcard include/config/INIT_ON_FREE_DEFAULT_ON) \
    $(wildcard include/config/DEBUG_PAGEALLOC) \
    $(wildcard include/config/ARCH_WANT_OPTIMIZE_DAX_VMEMMAP) \
    $(wildcard include/config/HUGETLBFS) \
    $(wildcard include/config/MAPPING_DIRTY_HELPERS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mmap_lock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/tracepoint-defs.h \
    $(wildcard include/config/TRACEPOINTS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/static_key.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/range.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/percpu-refcount.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bit_spinlock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/shrinker.h \
    $(wildcard include/config/SHRINKER_DEBUG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page_ext.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stacktrace.h \
    $(wildcard include/config/ARCH_STACKWALK) \
    $(wildcard include/config/STACKTRACE) \
    $(wildcard include/config/HAVE_RELIABLE_STACKTRACE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stackdepot.h \
    $(wildcard include/config/STACKDEPOT) \
    $(wildcard include/config/STACKDEPOT_MAX_FRAMES) \
    $(wildcard include/config/STACKDEPOT_ALWAYS_INIT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page_ref.h \
    $(wildcard include/config/DEBUG_PAGE_REF) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sizes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pgtable.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/HIGHPTE) \
    $(wildcard include/config/ARCH_HAS_NONLEAF_PMD_YOUNG) \
    $(wildcard include/config/ARCH_HAS_HW_PTE_YOUNG) \
    $(wildcard include/config/GUP_GET_PXX_LOW_HIGH) \
    $(wildcard include/config/ARCH_WANT_PMD_MKWRITE) \
    $(wildcard include/config/HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD) \
    $(wildcard include/config/HAVE_ARCH_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_ENABLE_THP_MIGRATION) \
    $(wildcard include/config/HAVE_ARCH_HUGE_VMAP) \
    $(wildcard include/config/X86_ESPFIX64) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pgtable.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pgtable_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/pgtable-nop4d.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/adi.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/adi_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/tlbflush.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/tlbflush_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mmu_context.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mmu_context_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/mm_hooks.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/mmu_context.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/pgtable_uffd.h \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page_table_check.h \
    $(wildcard include/config/PAGE_TABLE_CHECK) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kasan.h \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kasan-enabled.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kasan-tags.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/memremap.h \
    $(wildcard include/config/DEVICE_PRIVATE) \
    $(wildcard include/config/PCI_P2PDMA) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ioport.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/slab.h \
    $(wildcard include/config/FAILSLAB) \
    $(wildcard include/config/KFENCE) \
    $(wildcard include/config/SLUB_TINY) \
    $(wildcard include/config/SLUB_DEBUG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/huge_mm.h \
    $(wildcard include/config/READ_ONLY_THP_FOR_FS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/coredump.h \
    $(wildcard include/config/CORE_DUMP_DEFAULT_ELF_HEADERS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/fs.h \
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
    $(wildcard include/config/BLOCK) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/wait_bit.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kdev_t.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/kdev_t.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dcache.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rculist_bl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/list_bl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/path.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/stat.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/stat.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/stat.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/highuid.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/list_lru.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/radix-tree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pid.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/capability.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/capability.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/semaphore.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/fcntl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/fcntl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/asm-generic/fcntl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/openat2.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/migrate_mode.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/percpu-rwsem.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcuwait.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/signal.h \
    $(wildcard include/config/DYNAMIC_SIGFRAME) \
    $(wildcard include/config/PROC_FS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/jobctl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/uaccess.h \
    $(wildcard include/config/ARCH_HAS_SUBPAGE_FAULTS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/uaccess.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/extable.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/uaccess_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/access_ok.h \
    $(wildcard include/config/ALTERNATE_USER_ADDRESS_SPACE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cred.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sysctl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/sysctl.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/user.h \
    $(wildcard include/config/VFIO_PCI_ZDEV_KVM) \
    $(wildcard include/config/IOMMUFD) \
    $(wildcard include/config/WATCH_QUEUE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ratelimit.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/posix-timers.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hrtimer_defs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/timerqueue.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rcu_sync.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/delayed_call.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/uuid.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/errseq.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ioprio.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/rt.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/iocontext.h \
    $(wildcard include/config/BLK_ICQ) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/ioprio.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/fs_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mount.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mnt_idmapping.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rw_hint.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/fs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/dqblk_xfs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dqblk_v1.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dqblk_v2.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dqblk_qtree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/projid.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/quota.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/vmstat.h \
    $(wildcard include/config/VM_EVENT_COUNTERS) \
    $(wildcard include/config/DEBUG_TLBFLUSH) \
    $(wildcard include/config/PER_VMA_LOCK_STATS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/vm_event_item.h \
    $(wildcard include/config/MEMORY_BALLOON) \
    $(wildcard include/config/BALLOON_COMPACTION) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pagemap.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/highmem.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cacheflush.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cacheflush.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/cacheflush_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kmsan.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dma-direction.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hardirq.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/context_tracking_state.h \
    $(wildcard include/config/CONTEXT_TRACKING_USER) \
    $(wildcard include/config/CONTEXT_TRACKING) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ftrace_irq.h \
    $(wildcard include/config/HWLAT_TRACER) \
    $(wildcard include/config/OSNOISE_TRACER) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/vtime.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING) \
    $(wildcard include/config/IRQ_TIME_ACCOUNTING) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/hardirq.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/hardirq_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/highmem-internal.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/hugetlb_inline.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/interrupt.h \
    $(wildcard include/config/IRQ_FORCED_THREADING) \
    $(wildcard include/config/GENERIC_IRQ_PROBE) \
    $(wildcard include/config/IRQ_TIMINGS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqreturn.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/irq.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/irq_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/sections.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/sections.h \
    $(wildcard include/config/HAVE_FUNCTION_DESCRIPTORS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kernel_stat.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/delay.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/delay.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/delay_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/seq_file.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/string_helpers.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ctype.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/string_choices.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/profile.h \
    $(wildcard include/config/PROFILING) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/memblock.h \
    $(wildcard include/config/ARCH_KEEP_MEMBLOCK) \
    $(wildcard include/config/HAVE_MEMBLOCK_PHYS_MAP) \
    $(wildcard include/config/MEMTEST) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/dma.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/vmalloc.h \
    $(wildcard include/config/HAVE_ARCH_HUGE_VMALLOC) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/vmalloc.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ftrace.h \
    $(wildcard include/config/HAVE_FUNCTION_GRAPH_RETVAL) \
    $(wildcard include/config/FUNCTION_TRACER) \
    $(wildcard include/config/DYNAMIC_FTRACE) \
    $(wildcard include/config/HAVE_DYNAMIC_FTRACE_WITH_ARGS) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_REGS) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_ARGS) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_DIRECT_CALLS) \
    $(wildcard include/config/STACK_TRACER) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_CALL_OPS) \
    $(wildcard include/config/FRAME_POINTER) \
    $(wildcard include/config/FUNCTION_GRAPH_RETVAL) \
    $(wildcard include/config/FUNCTION_PROFILER) \
    $(wildcard include/config/FTRACE_SYSCALLS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/trace_recursion.h \
    $(wildcard include/config/FTRACE_RECORD_RECURSION) \
    $(wildcard include/config/ARCH_WANTS_NO_INSTR) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/trace_clock.h \
  arch/sparc/include/generated/asm/trace_clock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/trace_clock.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kallsyms.h \
    $(wildcard include/config/KALLSYMS_ALL) \
    $(wildcard include/config/KALLSYMS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/buildid.h \
    $(wildcard include/config/STACKTRACE_BUILD_ID) \
    $(wildcard include/config/VMCORE_INFO) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/module.h \
    $(wildcard include/config/MODULES_TREE_LOOKUP) \
    $(wildcard include/config/ARCH_USES_CFI_TRAPS) \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/DEBUG_INFO_BTF_MODULES) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/MODULE_UNLOAD) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kmod.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/umh.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/elf.h \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/elf.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/elf_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/elf.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/elf-em.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sysfs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/idr.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kobject_ns.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rbtree_latch.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/error-injection.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/error-injection.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dynamic_debug.h \
  arch/sparc/include/generated/asm/module.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
    $(wildcard include/config/MODULES_USE_ELF_REL) \
    $(wildcard include/config/MODULES_USE_ELF_RELA) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ptrace.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pid_namespace.h \
    $(wildcard include/config/MEMFD_CREATE) \
    $(wildcard include/config/PID_NS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/nsproxy.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/ns_common.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/ptrace.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/seccomp.h \
    $(wildcard include/config/HAVE_ARCH_SECCOMP_FILTER) \
    $(wildcard include/config/SECCOMP_FILTER) \
    $(wildcard include/config/CHECKPOINT_RESTORE) \
    $(wildcard include/config/SECCOMP_CACHE_DEBUG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/seccomp.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/seccomp.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/unistd.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/unistd.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/unistd.h \
  arch/sparc/include/generated/uapi/asm/unistd_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/seccomp.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/ftrace.h \
    $(wildcard include/config/MCOUNT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cpu.h \
    $(wildcard include/config/GENERIC_CPU_DEVICES) \
    $(wildcard include/config/PM_SLEEP_SMP) \
    $(wildcard include/config/PM_SLEEP_SMP_NONZERO_CPU) \
    $(wildcard include/config/ARCH_HAS_CPU_FINALIZE_INIT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/node.h \
    $(wildcard include/config/HMEM_REPORTING) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/device.h \
    $(wildcard include/config/HAS_IOMEM) \
    $(wildcard include/config/GENERIC_MSI_IRQ) \
    $(wildcard include/config/ENERGY_MODEL) \
    $(wildcard include/config/PINCTRL) \
    $(wildcard include/config/DMA_OPS) \
    $(wildcard include/config/DMA_DECLARE_COHERENT) \
    $(wildcard include/config/DMA_CMA) \
    $(wildcard include/config/SWIOTLB) \
    $(wildcard include/config/SWIOTLB_DYNAMIC) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_DEVICE) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU_ALL) \
    $(wildcard include/config/DMA_OPS_BYPASS) \
    $(wildcard include/config/PM_SLEEP) \
    $(wildcard include/config/OF) \
    $(wildcard include/config/DEVTMPFS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/dev_printk.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/energy_model.h \
    $(wildcard include/config/SCHED_DEBUG) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/cpufreq.h \
    $(wildcard include/config/CPU_FREQ) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/topology.h \
    $(wildcard include/config/SCHED_CLUSTER) \
    $(wildcard include/config/SCHED_MC) \
    $(wildcard include/config/CPU_FREQ_GOV_SCHEDUTIL) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/idle.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/sched/sd_flags.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/klist.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pm.h \
    $(wildcard include/config/VT_CONSOLE_SLEEP) \
    $(wildcard include/config/CXL_SUSPEND) \
    $(wildcard include/config/PM) \
    $(wildcard include/config/PM_CLK) \
    $(wildcard include/config/PM_GENERIC_DOMAINS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/device/bus.h \
    $(wildcard include/config/ACPI) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/device/class.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/device/driver.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/device.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/openprom.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/of.h \
    $(wildcard include/config/OF_DYNAMIC) \
    $(wildcard include/config/SPARC) \
    $(wildcard include/config/OF_PROMTREE) \
    $(wildcard include/config/OF_KOBJ) \
    $(wildcard include/config/OF_NUMA) \
    $(wildcard include/config/OF_OVERLAY) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mod_devicetable.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/mei.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/mei_uuid.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/property.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/fwnode.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/prom.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/of_pdt.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/proc_fs.h \
    $(wildcard include/config/PROC_PID_ARCH_STATUS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqdomain.h \
    $(wildcard include/config/IRQ_DOMAIN_HIERARCHY) \
    $(wildcard include/config/GENERIC_IRQ_DEBUGFS) \
    $(wildcard include/config/IRQ_DOMAIN) \
    $(wildcard include/config/IRQ_DOMAIN_NOMAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqdomain_defs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/irqhandler.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pm_wakeup.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cpuhotplug.h \
    $(wildcard include/config/HOTPLUG_CORE_SYNC_DEAD) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cpu_smt.h \
    $(wildcard include/config/HOTPLUG_SMT) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kgdb.h \
    $(wildcard include/config/HAVE_ARCH_KGDB) \
    $(wildcard include/config/SERIAL_KGDB_NMI) \
    $(wildcard include/config/KGDB_HONOUR_BLOCKLIST) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kprobes.h \
    $(wildcard include/config/KRETPROBE_ON_RETHOOK) \
    $(wildcard include/config/KPROBES_SANITY_TEST) \
    $(wildcard include/config/OPTPROBES) \
    $(wildcard include/config/KPROBES_ON_FTRACE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/objpool.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/rethook.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/kprobes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/kprobes.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/kgdb.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/head.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/head_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/hvtramp.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/io.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/io_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/pci_iomap.h \
    $(wildcard include/config/NO_GENERIC_PCI_IOPORT_MAP) \
    $(wildcard include/config/HAS_IOPORT_MAP) \
    $(wildcard include/config/GENERIC_PCI_IOMAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/io.h \
    $(wildcard include/config/GENERIC_IOMAP) \
    $(wildcard include/config/TRACE_MMIO_ACCESS) \
    $(wildcard include/config/GENERIC_IOREMAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/logic_pio.h \
    $(wildcard include/config/INDIRECT_PIO) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/setup.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/setup.h \
  arch/sparc/include/generated/asm/irq_regs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/irq_regs.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/oplib.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/oplib_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/tlb.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/tlb_64.h \
    $(wildcard include/config/MMU_GATHER_RCU_TABLE_FREE) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/swap.h \
    $(wildcard include/config/THP_SWAP) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/memcontrol.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cgroup.h \
    $(wildcard include/config/DEBUG_CGROUP_REF) \
    $(wildcard include/config/CGROUP_CPUACCT) \
    $(wildcard include/config/SOCK_CGROUP_DATA) \
    $(wildcard include/config/CGROUP_DATA) \
    $(wildcard include/config/CGROUP_BPF) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/cgroupstats.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/taskstats.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/user_namespace.h \
    $(wildcard include/config/INOTIFY_USER) \
    $(wildcard include/config/FANOTIFY) \
    $(wildcard include/config/BINFMT_MISC) \
    $(wildcard include/config/PERSISTENT_KEYRINGS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/cgroup-defs.h \
    $(wildcard include/config/CGROUP_NET_CLASSID) \
    $(wildcard include/config/CGROUP_NET_PRIO) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/u64_stats_sync.h \
  arch/sparc/include/generated/asm/local64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/local64.h \
  arch/sparc/include/generated/asm/local.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/local.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bpf-cgroup-defs.h \
    $(wildcard include/config/BPF_LSM) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/psi_types.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/kthread.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/page_counter.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/vmpressure.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/eventfd.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/eventfd.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/writeback.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/flex_proportions.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/backing-dev-defs.h \
    $(wildcard include/config/DEBUG_FS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/blk_types.h \
    $(wildcard include/config/FAIL_MAKE_REQUEST) \
    $(wildcard include/config/BLK_CGROUP_IOCOST) \
    $(wildcard include/config/BLK_INLINE_ENCRYPTION) \
    $(wildcard include/config/BLK_DEV_INTEGRITY) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/bvec.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/pagevec.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/uapi/linux/mempolicy.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/asm-generic/tlb.h \
    $(wildcard include/config/MMU_GATHER_TABLE_FREE) \
    $(wildcard include/config/MMU_GATHER_HAVE_TABLE_FREE) \
    $(wildcard include/config/MMU_GATHER_NO_GATHER) \
    $(wildcard include/config/MMU_GATHER_PAGE_SIZE) \
    $(wildcard include/config/MMU_GATHER_NO_RANGE) \
    $(wildcard include/config/MMU_GATHER_NO_FLUSH_CACHE) \
    $(wildcard include/config/MMU_GATHER_MERGE_VMAS) \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/mmu_notifier.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/include/linux/interval_tree.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pgalloc.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pgalloc_64.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/mdesc.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/ldc.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/pcr.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/kernel/cpumap.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/kernel/kernel.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/asm/traps.h \
  /root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/parent/linux/arch/sparc/include/uapi/asm/traps.h \

arch/sparc/kernel/smp_64.o: $(deps_arch/sparc/kernel/smp_64.o)

$(deps_arch/sparc/kernel/smp_64.o):
#SYMVER cpu_sibling_map 0x92e1cd02
#SYMVER cpu_core_map 0x1c9d159d
#SYMVER cpu_core_sib_map 0x9d72c148
#SYMVER cpu_core_sib_cache_map 0x8aa3845d
