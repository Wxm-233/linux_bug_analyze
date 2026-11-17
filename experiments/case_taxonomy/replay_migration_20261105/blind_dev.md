## A032

### 真实补丁T

```diff
commit 656f9aec07dba7c61d469727494a5d1b18d0bef4
Subject: LoongArch: Ensure FP/SIMD registers in the core dump file is up to date


diff --git a/arch/loongarch/include/asm/fpu.h b/arch/loongarch/include/asm/fpu.h
index b541f6248837..c2d8962fda00 100644
--- a/arch/loongarch/include/asm/fpu.h
+++ b/arch/loongarch/include/asm/fpu.h
@@ -173,16 +173,30 @@ static inline void restore_fp(struct task_struct *tsk)
 		_restore_fp(&tsk->thread.fpu);
 }
 
-static inline union fpureg *get_fpu_regs(struct task_struct *tsk)
+static inline void save_fpu_regs(struct task_struct *tsk)
 {
+	unsigned int euen;
+
 	if (tsk == current) {
 		preempt_disable();
-		if (is_fpu_owner())
+
+		euen = csr_read32(LOONGARCH_CSR_EUEN);
+
+#ifdef CONFIG_CPU_HAS_LASX
+		if (euen & CSR_EUEN_LASXEN)
+			_save_lasx(&current->thread.fpu);
+		else
+#endif
+#ifdef CONFIG_CPU_HAS_LSX
+		if (euen & CSR_EUEN_LSXEN)
+			_save_lsx(&current->thread.fpu);
+		else
+#endif
+		if (euen & CSR_EUEN_FPEN)
 			_save_fp(&current->thread.fpu);
+
 		preempt_enable();
 	}
-
-	return tsk->thread.fpu.fpr;
 }
 
 static inline int is_simd_owner(void)
diff --git a/arch/loongarch/kernel/ptrace.c b/arch/loongarch/kernel/ptrace.c
index a0767c3a0f0a..f72adbf530c6 100644
--- a/arch/loongarch/kernel/ptrace.c
+++ b/arch/loongarch/kernel/ptrace.c
@@ -147,6 +147,8 @@ static int fpr_get(struct task_struct *target,
 {
 	int r;
 
+	save_fpu_regs(target);
+
 	if (sizeof(target->thread.fpu.fpr[0]) == sizeof(elf_fpreg_t))
 		r = gfpr_get(target, &to);
 	else
@@ -278,6 +280,8 @@ static int simd_get(struct task_struct *target,
 {
 	const unsigned int wr_size = NUM_FPU_REGS * regset->size;
 
+	save_fpu_regs(target);
+
 	if (!tsk_used_math(target)) {
 		/* The task hasn't used FP or LSX, fill with 0xff */
 		copy_pad_fprs(target, regset, &to, 0);
```

### X

```diff
diff --git a/arch/loongarch/kernel/ptrace.c b/arch/loongarch/kernel/ptrace.c
--- a/arch/loongarch/kernel/ptrace.c
+++ b/arch/loongarch/kernel/ptrace.c
@@ -50,6 +50,20 @@
 	set_stopped_child_used_math(target);
 }
 
+/*
+ * Make sure thread.fpu holds the latest register values when the target
+ * is the current task (e.g. while dumping core), since the live state is
+ * otherwise only saved at context switch.
+ */
+static void sync_fpu_state(struct task_struct *target)
+{
+	if (target != current)
+		return;
+
+	preempt_disable();
+	if (is_fpu_owner())
+		save_fp(current);
+	preempt_enable();
+}
+
 /*
  * Called by kernel/ptrace.c when detaching..
  *
@@ -150,6 +164,8 @@
 {
 	int r;
 
+	sync_fpu_state(target);
+
 	if (sizeof(target->thread.fpu.fpr[0]) == sizeof(elf_fpreg_t))
 		r = gfpr_get(target, &to);
 	else
@@ -255,6 +271,8 @@
 {
 	const unsigned int wr_size = NUM_FPU_REGS * regset->size;
 
+	sync_fpu_state(target);
+
 	if (!tsk_used_math(target)) {
 		/* The task hasn't used FP or LSX, fill with 0xff */
 		copy_pad_fprs(target, regset, &to, 0);
```

### Y

```diff
diff --git a/arch/loongarch/kernel/ptrace.c b/arch/loongarch/kernel/ptrace.c
--- a/arch/loongarch/kernel/ptrace.c
+++ b/arch/loongarch/kernel/ptrace.c
@@ -147,6 +147,9 @@ static int fpr_get(struct task_struct *target,
 {
 	int r;
 
+	if (target == current)
+		save_fp(target);
+
 	if (sizeof(target->thread.fpu.fpr[0]) == sizeof(elf_fpreg_t))
 		r = gfpr_get(target, &to);
 	else
@@ -334,6 +337,9 @@ static int simd_get(struct task_struct *target,
 {
 	const unsigned int wr_size = NUM_FPU_REGS * regset->size;
 
+	if (target == current)
+		save_fp(target);
+
 	if (!tsk_used_math(target)) {
 		/* The task hasn't used FP or LSX, fill with 0xff */
 		copy_pad_fprs(target, regset, &to, 0);
```

## A048

### 真实补丁T

```diff
commit ff4a2443ef88874943f6d8444fb86327ec6f96b0
Subject: LoongArch: Select THP_SWAP if HAVE_ARCH_TRANSPARENT_HUGEPAGE


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 24bce573dc2b..e22330064e98 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -70,6 +70,7 @@ config LOONGARCH
 	select ARCH_WANT_LD_ORPHAN_WARN
 	select ARCH_WANT_OPTIMIZE_HUGETLB_VMEMMAP
 	select ARCH_WANTS_NO_INSTR
+	select ARCH_WANTS_THP_SWAP if HAVE_ARCH_TRANSPARENT_HUGEPAGE
 	select BUILDTIME_TABLE_SORT
 	select COMMON_CLK
 	select CPU_PM
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -77,6 +77,7 @@ config LOONGARCH
 	select ARCH_WANT_LD_ORPHAN_WARN
 	select ARCH_WANT_OPTIMIZE_HUGETLB_VMEMMAP
 	select ARCH_WANTS_NO_INSTR
+	select ARCH_WANTS_THP_SWAP if HAVE_ARCH_TRANSPARENT_HUGEPAGE
 	select BUILDTIME_TABLE_SORT
 	select COMMON_CLK
 	select CPU_PM
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -77,6 +77,7 @@ config LOONGARCH
 	select ARCH_WANT_LD_ORPHAN_WARN
 	select ARCH_WANT_OPTIMIZE_HUGETLB_VMEMMAP
 	select ARCH_WANTS_NO_INSTR
+	select ARCH_WANTS_THP_SWAP if HAVE_ARCH_TRANSPARENT_HUGEPAGE
 	select BUILDTIME_TABLE_SORT
 	select COMMON_CLK
 	select CPU_PM
```

## A051

### 真实补丁T

```diff
commit 8c347042527058976e8a1cb10c0ae31e55145f76
Subject: LoongArch: KVM: Add dirty bitmap initially all set support


diff --git a/arch/loongarch/include/asm/kvm_host.h b/arch/loongarch/include/asm/kvm_host.h
index 32c4948f534f..309ce329b747 100644
--- a/arch/loongarch/include/asm/kvm_host.h
+++ b/arch/loongarch/include/asm/kvm_host.h
@@ -37,6 +37,9 @@
 #define KVM_GUESTDBG_VALID_MASK		\
 	(KVM_GUESTDBG_ENABLE | KVM_GUESTDBG_USE_SW_BP | KVM_GUESTDBG_SINGLESTEP)
 
+#define KVM_DIRTY_LOG_MANUAL_CAPS	\
+	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | KVM_DIRTY_LOG_INITIALLY_SET)
+
 struct kvm_vm_stat {
 	struct kvm_vm_stat_generic generic;
 	u64 pages;
diff --git a/arch/loongarch/kvm/mmu.c b/arch/loongarch/kvm/mmu.c
index f1ed1c5296cf..1057bb984ba0 100644
--- a/arch/loongarch/kvm/mmu.c
+++ b/arch/loongarch/kvm/mmu.c
@@ -467,6 +467,13 @@ void kvm_arch_commit_memory_region(struct kvm *kvm,
 	 *		kvm_arch_flush_shadow_memslot()
 	 */
 	if (!(old_flags & KVM_MEM_LOG_DIRTY_PAGES) && log_dirty_pages) {
+		/*
+		 * Initially-all-set does not require write protecting any page
+		 * because they're all assumed to be dirty.
+		 */
+		if (kvm_dirty_log_manual_protect_and_init_set(kvm))
+			return;
+
 		spin_lock(&kvm->mmu_lock);
 		/* Write protect GPA page table entries */
 		needs_flush = kvm_mkclean_gpa_pt(kvm, new->base_gfn,
```

### X

```diff
diff --git a/arch/loongarch/include/asm/kvm_host.h b/arch/loongarch/include/asm/kvm_host.h
--- a/arch/loongarch/include/asm/kvm_host.h
+++ b/arch/loongarch/include/asm/kvm_host.h
@@ -30,6 +30,9 @@
 #define KVM_HALT_POLL_NS_DEFAULT	500000
 #define KVM_REQ_TLB_FLUSH_GPA		KVM_ARCH_REQ(0)
 
+#define KVM_DIRTY_LOG_MANUAL_CAPS	\
+	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | KVM_DIRTY_LOG_INITIALLY_SET)
+
 #define KVM_GUESTDBG_SW_BP_MASK		\
 	(KVM_GUESTDBG_ENABLE | KVM_GUESTDBG_USE_SW_BP)
 #define KVM_GUESTDBG_VALID_MASK		\
diff --git a/arch/loongarch/kvm/mmu.c b/arch/loongarch/kvm/mmu.c
--- a/arch/loongarch/kvm/mmu.c
+++ b/arch/loongarch/kvm/mmu.c
@@ -xxx,7 +xxx,13 @@
 	 * MOVE/DELETE:	The old mappings will already have been cleaned up by
 	 *		kvm_arch_flush_shadow_memslot()
 	 */
-	if (!(old_flags & KVM_MEM_LOG_DIRTY_PAGES) && log_dirty_pages) {
+	if (!(old_flags & KVM_MEM_LOG_DIRTY_PAGES) && log_dirty_pages &&
+	    /*
+	     * With initial-all-set, all pages are reported dirty already,
+	     * so no need to write protect them now; userspace clears the
+	     * dirty log gradually in small chunks.
+	     */
+	    !kvm_dirty_log_manual_protect_and_init_set(kvm)) {
 		spin_lock(&kvm->mmu_lock);
 		/* Write protect GPA page table entries */
 		needs_flush = kvm_mkclean_gpa_pt(kvm, new->base_gfn,
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/kvm_host.h b/arch/loongarch/include/asm/kvm_host.h
--- a/arch/loongarch/include/asm/kvm_host.h
+++ b/arch/loongarch/include/asm/kvm_host.h
@@ -34,6 +34,9 @@
 #define KVM_HALT_POLL_NS_DEFAULT	500000
 #define KVM_REQ_TLB_FLUSH_GPA		KVM_ARCH_REQ(0)
 
+#define KVM_DIRTY_LOG_MANUAL_CAPS	\
+	(KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE | KVM_DIRTY_LOG_INITIALLY_SET)
+
 #define KVM_GUESTDBG_SW_BP_MASK		\
 	(KVM_GUESTDBG_ENABLE | KVM_GUESTDBG_USE_SW_BP)
 #define KVM_GUESTDBG_VALID_MASK		\
diff --git a/arch/loongarch/kvm/mmu.c b/arch/loongarch/kvm/mmu.c
--- a/arch/loongarch/kvm/mmu.c
+++ b/arch/loongarch/kvm/mmu.c
@@ -445,12 +445,18 @@
 	 *		kvm_arch_flush_shadow_memslot()
 	 */
 	if (!(old_flags & KVM_MEM_LOG_DIRTY_PAGES) && log_dirty_pages) {
-		spin_lock(&kvm->mmu_lock);
-		/* Write protect GPA page table entries */
-		needs_flush = kvm_mkclean_gpa_pt(kvm, new->base_gfn,
-					new->base_gfn + new->npages);
-		spin_unlock(&kvm->mmu_lock);
-		if (needs_flush)
-			kvm_flush_remote_tlbs(kvm);
+		/*
+		 * With initial-all-set, all pages are already reported as
+		 * dirty, so they will be write protected gradually.
+		 */
+		if (!kvm_dirty_log_manual_protect_and_init_set(kvm)) {
+			spin_lock(&kvm->mmu_lock);
+			/* Write protect GPA page table entries */
+			needs_flush = kvm_mkclean_gpa_pt(kvm, new->base_gfn,
+						new->base_gfn + new->npages);
+			spin_unlock(&kvm->mmu_lock);
+			if (needs_flush)
+				kvm_flush_remote_tlbs(kvm);
+		}
 	}
 }
```

## A052

### 真实补丁T

```diff
commit e05d4cd9b895c503dcf19c0ed9ebb8d393b220ec
Subject: LoongArch: Add support for relocating the kernel with RELR relocation


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index 9687b1d24126..f5df69ad70a6 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -610,6 +610,7 @@ config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
 
 config RELOCATABLE
 	bool "Relocatable kernel"
+	select ARCH_HAS_RELR
 	help
 	  This builds the kernel as a Position Independent Executable (PIE),
 	  which retains all relocation metadata required, so as to relocate
diff --git a/arch/loongarch/include/asm/asmmacro.h b/arch/loongarch/include/asm/asmmacro.h
index 655db7d7a427..8d7f501b0a12 100644
--- a/arch/loongarch/include/asm/asmmacro.h
+++ b/arch/loongarch/include/asm/asmmacro.h
@@ -609,6 +609,7 @@
 	lu32i.d	\reg, 0
 	lu52i.d	\reg, \reg, 0
 	.pushsection ".la_abs", "aw", %progbits
+	.p2align 3
 	.dword	766b
 	.dword	\sym
 	.popsection
diff --git a/arch/loongarch/include/asm/setup.h b/arch/loongarch/include/asm/setup.h
index ee52fb1e9963..3c2fb16b11b6 100644
--- a/arch/loongarch/include/asm/setup.h
+++ b/arch/loongarch/include/asm/setup.h
@@ -34,6 +34,11 @@ extern long __la_abs_end;
 extern long __rela_dyn_begin;
 extern long __rela_dyn_end;
 
+#ifdef CONFIG_RELR
+extern long __relr_dyn_begin;
+extern long __relr_dyn_end;
+#endif
+
 extern unsigned long __init relocate_kernel(void);
 
 #endif
diff --git a/arch/loongarch/kernel/relocate.c b/arch/loongarch/kernel/relocate.c
index e3836f0b9bd8..50c469067f3a 100644
--- a/arch/loongarch/kernel/relocate.c
+++ b/arch/loongarch/kernel/relocate.c
@@ -38,6 +38,24 @@ static inline void __init relocate_relative(void)
 		relocated_addr = (Elf64_Addr)RELOCATED(relocated_addr);
 		*(Elf64_Addr *)RELOCATED(addr) = relocated_addr;
 	}
+
+#ifdef CONFIG_RELR
+	u64 *addr = NULL;
+	u64 *relr = (u64 *)&__relr_dyn_begin;
+	u64 *relr_end = (u64 *)&__relr_dyn_end;
+
+	for ( ; relr < relr_end; relr++) {
+		if ((*relr & 1) == 0) {
+			addr = (u64 *)(*relr + reloc_offset);
+			*addr++ += reloc_offset;
+		} else {
+			for (u64 *p = addr, r = *relr >> 1; r; p++, r >>= 1)
+				if (r & 1)
+					*p += reloc_offset;
+			addr += 63;
+		}
+	}
+#endif
 }
 
 static inline void __init relocate_absolute(long random_offset)
diff --git a/arch/loongarch/kernel/vmlinux.lds.S b/arch/loongarch/kernel/vmlinux.lds.S
index 3c7595342730..08ea921cdec1 100644
--- a/arch/loongarch/kernel/vmlinux.lds.S
+++ b/arch/loongarch/kernel/vmlinux.lds.S
@@ -113,6 +113,14 @@ SECTIONS
 		__rela_dyn_end = .;
 	}
 
+#ifdef CONFIG_RELR
+	.relr.dyn : ALIGN(8) {
+		__relr_dyn_begin = .;
+		 *(.relr.dyn)
+		__relr_dyn_end = .;
+	}
+#endif
+
 	.data.rel : { *(.data.rel*) }
 
 #ifdef CONFIG_RELOCATABLE
```

### X

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -1,6 +1,7 @@
 config RELOCATABLE
 	bool "Relocatable kernel"
+	select ARCH_HAS_RELR
 	help
 	  This builds the kernel as a Position Independent Executable (PIE),
 	  which retains all relocation metadata required, so as to relocate
diff --git a/arch/loongarch/kernel/vmlinux.lds.S b/arch/loongarch/kernel/vmlinux.lds.S
--- a/arch/loongarch/kernel/vmlinux.lds.S
+++ b/arch/loongarch/kernel/vmlinux.lds.S
@@ -1,6 +1,14 @@
 		 *(.rela.dyn) *(.rela*)
 		__rela_dyn_end = .;
 	}
 
+#ifdef CONFIG_RELR
+	.relr.dyn : ALIGN(8) {
+		__relr_dyn_begin = .;
+		*(.relr.dyn)
+		__relr_dyn_end = .;
+	}
+#endif
+
 	.data.rel : { *(.data.rel*) }
 
 #ifdef CONFIG_RELOCATABLE
```

### Y

```diff
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -fix,6 +fix,7 @@ config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
 
 config RELOCATABLE
 	bool "Relocatable kernel"
+	select ARCH_HAS_RELR
 	help
 	  This builds the kernel as a Position Independent Executable (PIE),
 	  which retains all relocation metadata required, so as to relocate
diff --git a/arch/loongarch/kernel/vmlinux.lds.S b/arch/loongarch/kernel/vmlinux.lds.S
--- a/arch/loongarch/kernel/vmlinux.lds.S
+++ b/arch/loongarch/kernel/vmlinux.lds.S
@@ -117,6 +117,14 @@ SECTIONS
 		__rela_dyn_end = .;
 	}
 
+#ifdef CONFIG_RELR
+	.relr.dyn : ALIGN(8) {
+		__relr_dyn_begin = .;
+		*(.relr.dyn)
+		__relr_dyn_end = .;
+	}
+#endif
+
 	.data.rel : { *(.data.rel*) }
 
 #ifdef CONFIG_RELOCATABLE
```

## A093

### 真实补丁T

```diff
commit 62cda5e54f7c5e773911b458dd4d10ee8c91b60b
Subject: LoongArch: kexec: Print out debugging message if required


diff --git a/arch/loongarch/kernel/machine_kexec.c b/arch/loongarch/kernel/machine_kexec.c
index e4b2bbc47e62..2d64b7c81e5e 100644
--- a/arch/loongarch/kernel/machine_kexec.c
+++ b/arch/loongarch/kernel/machine_kexec.c
@@ -39,34 +39,12 @@ static unsigned long systable_ptr;
 static unsigned long start_addr;
 static unsigned long first_ind_entry;
 
-static void kexec_image_info(const struct kimage *kimage)
-{
-	unsigned long i;
-
-	pr_debug("kexec kimage info:\n");
-	pr_debug("\ttype:        %d\n", kimage->type);
-	pr_debug("\tstart:       %lx\n", kimage->start);
-	pr_debug("\thead:        %lx\n", kimage->head);
-	pr_debug("\tnr_segments: %lu\n", kimage->nr_segments);
-
-	for (i = 0; i < kimage->nr_segments; i++) {
-		pr_debug("\t    segment[%lu]: %016lx - %016lx", i,
-			kimage->segment[i].mem,
-			kimage->segment[i].mem + kimage->segment[i].memsz);
-		pr_debug("\t\t0x%lx bytes, %lu pages\n",
-			(unsigned long)kimage->segment[i].memsz,
-			(unsigned long)kimage->segment[i].memsz /  PAGE_SIZE);
-	}
-}
-
 int machine_kexec_prepare(struct kimage *kimage)
 {
 	int i;
 	char *bootloader = "kexec";
 	void *cmdline_ptr = (void *)KEXEC_CMDLINE_ADDR;
 
-	kexec_image_info(kimage);
-
 	kimage->arch.efi_boot = fw_arg0;
 	kimage->arch.systable_ptr = fw_arg2;
```

### X

```diff
diff --git a/arch/loongarch/kernel/machine_kexec.c b/arch/loongarch/kernel/machine_kexec.c
--- a/arch/loongarch/kernel/machine_kexec.c
+++ b/arch/loongarch/kernel/machine_kexec.c
@@ -39,35 +39,12 @@ static unsigned long systable_ptr;
 static unsigned long start_addr;
 static unsigned long first_ind_entry;
 
-static void kexec_image_info(const struct kimage *kimage)
-{
-	unsigned long i;
-
-	pr_debug("kexec kimage info:\n");
-	pr_debug("\ttype:        %d\n", kimage->type);
-	pr_debug("\tstart:       %lx\n", kimage->start);
-	pr_debug("\thead:        %lx\n", kimage->head);
-	pr_debug("\tnr_segments: %lu\n", kimage->nr_segments);
-
-	for (i = 0; i < kimage->nr_segments; i++) {
-		pr_debug("\t    segment[%lu]: %016lx - %016lx", i,
-			kimage->segment[i].mem,
-			kimage->segment[i].mem + kimage->segment[i].memsz);
-		pr_debug("\t\t0x%lx bytes, %lu pages\n",
-			(unsigned long)kimage->segment[i].memsz,
-			(unsigned long)kimage->segment[i].memsz /  PAGE_SIZE);
-	}
-}
-
 int machine_kexec_prepare(struct kimage *kimage)
 {
 	int i;
 	char *bootloader = "kexec";
 	void *cmdline_ptr = (void *)KEXEC_CMDLINE_ADDR;
 
-	kexec_image_info(kimage);
-
 	kimage->arch.efi_boot = fw_arg0;
 	kimage->arch.systable_ptr = fw_arg2;
```

### Y

```diff
diff --git a/arch/loongarch/kernel/machine_kexec.c b/arch/loongarch/kernel/machine_kexec.c
--- a/arch/loongarch/kernel/machine_kexec.c
+++ b/arch/loongarch/kernel/machine_kexec.c
@@ -39,32 +39,12 @@ static unsigned long systable_ptr;
 static unsigned long start_addr;
 static unsigned long first_ind_entry;
 
-static void kexec_image_info(const struct kimage *kimage)
-{
-	unsigned long i;
-
-	pr_debug("kexec kimage info:\n");
-	pr_debug("\ttype:        %d\n", kimage->type);
-	pr_debug("\tstart:       %lx\n", kimage->start);
-	pr_debug("\thead:        %lx\n", kimage->head);
-	pr_debug("\tnr_segments: %lu\n", kimage->nr_segments);
-
-	for (i = 0; i < kimage->nr_segments; i++) {
-		pr_debug("\t    segment[%lu]: %016lx - %016lx", i,
-			kimage->segment[i].mem,
-			kimage->segment[i].mem + kimage->segment[i].memsz);
-		pr_debug("\t\t0x%lx bytes, %lu pages\n",
-			(unsigned long)kimage->segment[i].memsz,
-			(unsigned long)kimage->segment[i].memsz /  PAGE_SIZE);
-	}
-}
-
 int machine_kexec_prepare(struct kimage *kimage)
 {
 	int i;
 	char *bootloader = "kexec";
 	void *cmdline_ptr = (void *)KEXEC_CMDLINE_ADDR;
 
-	kexec_image_info(kimage);
-
 	kimage->arch.efi_boot = fw_arg0;
 	kimage->arch.systable_ptr = fw_arg2;
```

## L093

### 真实补丁T

```diff
commit 697f3342477170bdf8759157bdc19c0b7b3e9d14
Subject: LoongArch: Fix Kconfig item and left code related to CRASH_CORE


diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
index a5f300ec6f28..54ad04dacdee 100644
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -595,7 +595,7 @@ config ARCH_SELECTS_CRASH_DUMP
 	select RELOCATABLE
 
 config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
-	def_bool CRASH_CORE
+	def_bool CRASH_RESERVE
 
 config RELOCATABLE
 	bool "Relocatable kernel"
diff --git a/arch/loongarch/include/asm/crash_core.h b/arch/loongarch/include/asm/crash_reserve.h
similarity index 75%
rename from arch/loongarch/include/asm/crash_core.h
rename to arch/loongarch/include/asm/crash_reserve.h
index 218bdbfa527b..a1d9b84b1c7d 100644
--- a/arch/loongarch/include/asm/crash_core.h
+++ b/arch/loongarch/include/asm/crash_reserve.h
@@ -1,6 +1,6 @@
 /* SPDX-License-Identifier: GPL-2.0-only */
-#ifndef _LOONGARCH_CRASH_CORE_H
-#define _LOONGARCH_CRASH_CORE_H
+#ifndef _LOONGARCH_CRASH_RESERVE_H
+#define _LOONGARCH_CRASH_RESERVE_H
 
 #define CRASH_ALIGN			SZ_2M
```

### X

```diff
diff --git a/arch/loongarch/include/asm/crash_core.h b/arch/loongarch/include/asm/crash_reserve.h
similarity index 76%
rename from arch/loongarch/include/asm/crash_core.h
rename to arch/loongarch/include/asm/crash_reserve.h
--- a/arch/loongarch/include/asm/crash_core.h
+++ b/arch/loongarch/include/asm/crash_reserve.h
@@ -1,6 +1,6 @@
 /* SPDX-License-Identifier: GPL-2.0-only */
-#ifndef _LOONGARCH_CRASH_CORE_H
-#define _LOONGARCH_CRASH_CORE_H
+#ifndef _LOONGARCH_CRASH_RESERVE_H
+#define _LOONGARCH_CRASH_RESERVE_H
 
 #define CRASH_ALIGN			SZ_2M
 
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -1,3 +1,3 @@
 config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
-	def_bool CRASH_CORE
+	def_bool CRASH_RESERVE
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/crash_core.h b/arch/loongarch/include/asm/crash_reserve.h
similarity index 76%
rename from arch/loongarch/include/asm/crash_core.h
rename to arch/loongarch/include/asm/crash_reserve.h
--- a/arch/loongarch/include/asm/crash_core.h
+++ b/arch/loongarch/include/asm/crash_reserve.h
@@ -1,6 +1,6 @@
 /* SPDX-License-Identifier: GPL-2.0-only */
-#ifndef _LOONGARCH_CRASH_CORE_H
-#define _LOONGARCH_CRASH_CORE_H
+#ifndef _LOONGARCH_CRASH_RESERVE_H
+#define _LOONGARCH_CRASH_RESERVE_H
 
 #define CRASH_ALIGN			SZ_2M
 
diff --git a/arch/loongarch/Kconfig b/arch/loongarch/Kconfig
--- a/arch/loongarch/Kconfig
+++ b/arch/loongarch/Kconfig
@@ -1,3 +1,3 @@
 config ARCH_HAS_GENERIC_CRASHKERNEL_RESERVATION
-	def_bool CRASH_CORE
+	def_bool CRASH_RESERVE
```

## L112

### 真实补丁T

```diff
commit 0078e94a4733454d1ffa3888afe88bf19c81b91c
Subject: LoongArch: Rename GCC_PLUGIN_STACKLEAK to KSTACK_ERASE


diff --git a/arch/loongarch/include/asm/stackframe.h b/arch/loongarch/include/asm/stackframe.h
index 3eda298702b1..5cb568a60cf8 100644
--- a/arch/loongarch/include/asm/stackframe.h
+++ b/arch/loongarch/include/asm/stackframe.h
@@ -58,7 +58,7 @@
 	.endm
 
 	.macro STACKLEAK_ERASE
-#ifdef CONFIG_GCC_PLUGIN_STACKLEAK
+#ifdef CONFIG_KSTACK_ERASE
 	bl	stackleak_erase_on_task_stack
 #endif
 	.endm
```

### X

```diff
diff --git a/arch/loongarch/include/asm/stackframe.h b/arch/loongarch/include/asm/stackframe.h
--- a/arch/loongarch/include/asm/stackframe.h
+++ b/arch/loongarch/include/asm/stackframe.h
@@ -56,7 +56,7 @@
 	.endm
 
 	.macro STACKLEAK_ERASE
-#ifdef CONFIG_GCC_PLUGIN_STACKLEAK
+#ifdef CONFIG_KSTACK_ERASE
 	bl	stackleak_erase_on_task_stack
 #endif
 	.endm
```

### Y

```diff
diff --git a/arch/loongarch/include/asm/stackframe.h b/arch/loongarch/include/asm/stackframe.h
--- a/arch/loongarch/include/asm/stackframe.h
+++ b/arch/loongarch/include/asm/stackframe.h
@@ -56,7 +56,7 @@
 	.endm
 
 	.macro STACKLEAK_ERASE
-#ifdef CONFIG_GCC_PLUGIN_STACKLEAK
+#ifdef CONFIG_KSTACK_ERASE
 	bl	stackleak_erase_on_task_stack
 #endif
 	.endm
```

## L123

### 真实补丁T

```diff
commit e82406c7cbdd368c5459b8a45e118811d2ba0794
Subject: LoongArch: BPF: No support of struct argument in trampoline programs


diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
index 33e8942cc961..8c3c211983f9 100644
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1492,6 +1492,12 @@ static int __arch_prepare_bpf_trampoline(struct jit_ctx *ctx, struct bpf_tramp_i
 	if (m->nr_args > LOONGARCH_MAX_REG_ARGS)
 		return -ENOTSUPP;
 
+	/* FIXME: No support of struct argument */
+	for (i = 0; i < m->nr_args; i++) {
+		if (m->arg_flags[i] & BTF_FMODEL_STRUCT_ARG)
+			return -ENOTSUPP;
+	}
+
 	if (flags & (BPF_TRAMP_F_ORIG_STACK | BPF_TRAMP_F_SHARE_IPMODIFY))
 		return -ENOTSUPP;
```

### X

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 	if (m->nr_args > LOONGARCH_MAX_REG_ARGS)
 		return -ENOTSUPP;
 
+	/* don't support struct argument */
+	for (i = 0; i < MAX_BPF_FUNC_ARGS; i++) {
+		if (m->arg_flags[i] & BTF_FMODEL_STRUCT_ARG)
+			return -ENOTSUPP;
+	}
+
 	if (flags & (BPF_TRAMP_F_ORIG_STACK | BPF_TRAMP_F_SHARE_IPMODIFY))
 		return -ENOTSUPP;
```

### Y

```diff
diff --git a/arch/loongarch/net/bpf_jit.c b/arch/loongarch/net/bpf_jit.c
--- a/arch/loongarch/net/bpf_jit.c
+++ b/arch/loongarch/net/bpf_jit.c
@@ -1,3 +1,3 @@
 	if (m->nr_args > LOONGARCH_MAX_REG_ARGS)
 		return -ENOTSUPP;
 
+	/* don't support struct argument */
+	for (i = 0; i < MAX_BPF_FUNC_ARGS; i++) {
+		if (m->arg_flags[i] & BTF_FMODEL_STRUCT_ARG)
+			return -ENOTSUPP;
+	}
+
 	if (flags & (BPF_TRAMP_F_ORIG_STACK | BPF_TRAMP_F_SHARE_IPMODIFY))
 		return -ENOTSUPP;
```

## R048

### 真实补丁T

```diff
commit 8762606ae22e71ec65249cdbf809e3dc7ea8ea1e
Subject: riscv/purgatory: Do not use fortified string functions


diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
index 5730797a6b40..8c73360c42bb 100644
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -31,7 +31,7 @@ $(obj)/strncmp.o: $(srctree)/arch/riscv/lib/strncmp.S FORCE
 $(obj)/sha256.o: $(srctree)/lib/crypto/sha256.c FORCE
 	$(call if_changed_rule,cc_o_c)
 
-CFLAGS_sha256.o := -D__DISABLE_EXPORTS
+CFLAGS_sha256.o := -D__DISABLE_EXPORTS -D__NO_FORTIFY
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
```

### X

```diff
diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -32,7 +32,7 @@ $(obj)/strncmp.o: $(srctree)/arch/riscv/lib/strncmp.S FORCE
 $(obj)/sha256.o: $(srctree)/lib/crypto/sha256.c FORCE
 	$(call if_changed_rule,cc_o_c)
 
-CFLAGS_sha256.o := -D__DISABLE_EXPORTS
+CFLAGS_sha256.o := -D__DISABLE_EXPORTS -D__NO_FORTIFY
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
```

### Y

```diff
diff --git a/arch/riscv/purgatory/Makefile b/arch/riscv/purgatory/Makefile
--- a/arch/riscv/purgatory/Makefile
+++ b/arch/riscv/purgatory/Makefile
@@ -30,7 +30,7 @@ $(obj)/strncmp.o: $(srctree)/arch/riscv/lib/strncmp.S FORCE
 $(obj)/sha256.o: $(srctree)/lib/crypto/sha256.c FORCE
 	$(call if_changed_rule,cc_o_c)
 
-CFLAGS_sha256.o := -D__DISABLE_EXPORTS
+CFLAGS_sha256.o := -D__DISABLE_EXPORTS -D__NO_FORTIFY
 CFLAGS_string.o := -D__DISABLE_EXPORTS
 CFLAGS_ctype.o := -D__DISABLE_EXPORTS
```

## R064

### 真实补丁T

```diff
commit 4eb2eb1b4c0eb07793c240744843498564a67b83
Subject: riscv,mmio: Fix readX()-to-delay() ordering


diff --git a/arch/riscv/include/asm/mmio.h b/arch/riscv/include/asm/mmio.h
index aff6c33ab0c0..4c58ee7f95ec 100644
--- a/arch/riscv/include/asm/mmio.h
+++ b/arch/riscv/include/asm/mmio.h
@@ -101,9 +101,9 @@ static inline u64 __raw_readq(const volatile void __iomem *addr)
  * Relaxed I/O memory access primitives. These follow the Device memory
  * ordering rules but do not guarantee any ordering relative to Normal memory
  * accesses.  These are defined to order the indicated access (either a read or
- * write) with all other I/O memory accesses. Since the platform specification
- * defines that all I/O regions are strongly ordered on channel 2, no explicit
- * fences are required to enforce this ordering.
+ * write) with all other I/O memory accesses to the same peripheral. Since the
+ * platform specification defines that all I/O regions are strongly ordered on
+ * channel 0, no explicit fences are required to enforce this ordering.
  */
 /* FIXME: These are now the same as asm-generic */
 #define __io_rbr()		do {} while (0)
@@ -125,14 +125,14 @@ static inline u64 __raw_readq(const volatile void __iomem *addr)
 #endif
 
 /*
- * I/O memory access primitives. Reads are ordered relative to any
- * following Normal memory access. Writes are ordered relative to any prior
- * Normal memory access.  The memory barriers here are necessary as RISC-V
+ * I/O memory access primitives.  Reads are ordered relative to any following
+ * Normal memory read and delay() loop.  Writes are ordered relative to any
+ * prior Normal memory write.  The memory barriers here are necessary as RISC-V
  * doesn't define any ordering between the memory space and the I/O space.
  */
 #define __io_br()	do {} while (0)
-#define __io_ar(v)	__asm__ __volatile__ ("fence i,r" : : : "memory")
-#define __io_bw()	__asm__ __volatile__ ("fence w,o" : : : "memory")
+#define __io_ar(v)	({ __asm__ __volatile__ ("fence i,ir" : : : "memory"); })
+#define __io_bw()	({ __asm__ __volatile__ ("fence w,o" : : : "memory"); })
 #define __io_aw()	mmiowb_set_pending()
 
 #define readb(c)	({ u8  __v; __io_br(); __v = readb_cpu(c); __io_ar(__v); __v; })
```

### X

```diff
diff --git a/arch/riscv/include/asm/mmio.h b/arch/riscv/include/asm/mmio.h
--- a/arch/riscv/include/asm/mmio.h
+++ b/arch/riscv/include/asm/mmio.h
@@ -131,8 +131,14 @@
  * Normal memory access.  The memory barriers here are necessary as RISC-V
  * doesn't define any ordering between the memory space and the I/O space.
+ *
+ * __io_ar() also orders the I/O read against later I/O accesses, so a
+ * subsequent udelay() (which reads the time CSR) cannot be executed before
+ * the read has returned.
  */
 #define __io_br()	do {} while (0)
-#define __io_ar(v)	__asm__ __volatile__ ("fence i,r" : : : "memory")
+#define __io_ar(v)	({ __asm__ __volatile__ ("fence i,ir" : : : "memory"); })
 #define __io_bw()	__asm__ __volatile__ ("fence w,o" : : : "memory")
 #define __io_aw()	mmiowb_set_pending()
```

### Y

```diff
diff --git a/arch/riscv/include/asm/mmio.h b/arch/riscv/include/asm/mmio.h
--- a/arch/riscv/include/asm/mmio.h
+++ b/arch/riscv/include/asm/mmio.h
@@ -131,7 +131,7 @@
  * doesn't define any ordering between the memory space and the I/O space.
  */
 #define __io_br()	do {} while (0)
-#define __io_ar(v)	__asm__ __volatile__ ("fence i,r" : : : "memory")
+#define __io_ar(v)	__asm__ __volatile__ ("fence i,ir" : : : "memory")
 #define __io_bw()	__asm__ __volatile__ ("fence w,o" : : : "memory")
 #define __io_aw()	mmiowb_set_pending()
```
