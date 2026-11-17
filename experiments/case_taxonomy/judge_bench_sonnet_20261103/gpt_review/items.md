# 待复核条目（顺序已打乱）

## G01（A392）

**被检查的函数**：`arch/riscv/kernel/machine_kexec_file.c`中的`prepare_elf_headers`

**模型指出的问题**：只排除了 crashk_res，没有排除 crashk_low_res（低端 crashkernel 保留区），且 nr_ranges 只预留了 1 个额外槽位，不够再多分裂一次。

**真实修复的标题**：riscv: kexec_file: Fix crashk_low_res not exclude bug

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/machine_kexec_file.c b/arch/riscv/kernel/machine_kexec_file.c
index 59d4bbc848a8..fa2946aa9b8f 100644
--- a/arch/riscv/kernel/machine_kexec_file.c
+++ b/arch/riscv/kernel/machine_kexec_file.c
@@ -63,5 +63,5 @@ static int prepare_elf_headers(void **addr, unsigned long *sz)
 	int ret;
 
-	nr_ranges = 1; /* For exclusion of crashkernel region */
+	nr_ranges = 2; /* For exclusion of crashkernel region */
 	walk_system_ram_res(0, -1, &nr_ranges, get_nr_ram_ranges_callback);
 
@@ -78,6 +78,14 @@ static int prepare_elf_headers(void **addr, unsigned long *sz)
 	/* Exclude crashkernel region */
 	ret = crash_exclude_mem_range(cmem, crashk_res.start, crashk_res.end);
-	if (!ret)
-		ret = crash_prepare_elf64_headers(cmem, true, addr, sz);
+	if (ret)
+		goto out;
+
+	if (crashk_low_res.end) {
+		ret = crash_exclude_mem_range(cmem, crashk_low_res.start, crashk_low_res.end);
+		if (ret)
+			goto out;
+	}
+
+	ret = crash_prepare_elf64_headers(cmem, true, addr, sz);
 
 out:
```

## G02（A288）

**被检查的函数**：`arch/riscv/kernel/module.c`中的`module_alloc`

**模型指出的问题**：RISC-V 的 module_alloc 直接返回 __vmalloc_node_range 的结果，未在 KASAN 下调用 kasan_alloc_module_shadow 并在失败时 vfree。

**真实修复的标题**：riscv: Fix module_alloc() that did not reset the linear mapping permissions

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/module.c b/arch/riscv/kernel/module.c
index aac019ed63b1..862834bb1d64 100644
--- a/arch/riscv/kernel/module.c
+++ b/arch/riscv/kernel/module.c
@@ -895,5 +895,6 @@ void *module_alloc(unsigned long size)
 	return __vmalloc_node_range(size, 1, MODULES_VADDR,
 				    MODULES_END, GFP_KERNEL,
-				    PAGE_KERNEL, 0, NUMA_NO_NODE,
+				    PAGE_KERNEL, VM_FLUSH_RESET_PERMS,
+				    NUMA_NO_NODE,
 				    __builtin_return_address(0));
 }
```

## G03（A359）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：D8 的 GPA 上限检查使用 >=，会把结束于 GPA 空间顶端的合法 memslot 也拒绝；应改为 >（或比较 base_gfn + npages - 1）。

**真实修复的标题**：RISC-V: KVM: Remove automatic I/O mapping for VM_PFNMAP

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index 525fb5a330c0..58f5f3536ffd 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -172,5 +172,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 {
 	hva_t hva, reg_end, size;
-	gpa_t base_gpa;
 	bool writable;
 	int ret = 0;
@@ -191,5 +190,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	size = new->npages << PAGE_SHIFT;
 	reg_end = hva + size;
-	base_gpa = new->base_gfn << PAGE_SHIFT;
 	writable = !(new->flags & KVM_MEM_READONLY);
 
@@ -198,6 +196,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	/*
 	 * A memory region could potentially cover multiple VMAs, and
-	 * any holes between them, so iterate over all of them to find
-	 * out if we can map any of them right now.
+	 * any holes between them, so iterate over all of them.
 	 *
 	 *     +--------------------------------------------+
@@ -210,5 +207,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	do {
 		struct vm_area_struct *vma;
-		hva_t vm_start, vm_end;
+		hva_t vm_end;
 
 		vma = find_vma_intersection(current->mm, hva, reg_end);
@@ -226,14 +223,7 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 
 		/* Take the intersection of this VMA with the memory region */
-		vm_start = max(hva, vma->vm_start);
 		vm_end = min(reg_end, vma->vm_end);
 
 		if (vma->vm_flags & VM_PFNMAP) {
-			gpa_t gpa = base_gpa + (vm_start - hva);
-			phys_addr_t pa;
-
-			pa = (phys_addr_t)vma->vm_pgoff << PAGE_SHIFT;
-			pa += vm_start - vma->vm_start;
-
 			/* IO region dirty page logging not allowed */
 			if (new->flags & KVM_MEM_LOG_DIRTY_PAGES) {
@@ -241,19 +231,8 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 				goto out;
 			}
-
-			ret = kvm_riscv_mmu_ioremap(kvm, gpa, pa, vm_end - vm_start,
-						    writable, false);
-			if (ret)
-				break;
 		}
 		hva = vm_end;
 	} while (hva < reg_end);
 
-	if (change == KVM_MR_FLAGS_ONLY)
-		goto out;
-
-	if (ret)
-		kvm_riscv_mmu_iounmap(kvm, base_gpa, size);
-
 out:
 	mmap_read_unlock(current->mm);
```

## G04（A321）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`emit_atomic`

**模型指出的问题**：32 位 BPF_CMPXCHG 原子返回值未零扩展：RISC-V 用 rv_lr_w 将旧值符号扩展到 R0，CMPXCHG 路径在 fence 后缺少 emit_zextw(r0,r0,ctx)，导致 R0 高 32 位可能错误。

**真实修复的标题**：riscv, bpf: Make BPF_CMPXCHG fully ordered

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index 91bd5082c4d8..4cc631fa7039 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -551,6 +551,6 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 		jmp_offset = ninsns_rvoff(8);
 		emit(rv_bne(RV_REG_T2, r0, jmp_offset >> 1), ctx);
-		emit(is64 ? rv_sc_d(RV_REG_T3, rs, rd, 0, 0) :
-		     rv_sc_w(RV_REG_T3, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_sc_d(RV_REG_T3, rs, rd, 0, 1) :
+		     rv_sc_w(RV_REG_T3, rs, rd, 0, 1), ctx);
 		jmp_offset = ninsns_rvoff(-6);
 		emit(rv_bne(RV_REG_T3, 0, jmp_offset >> 1), ctx);
```

## G05（A393）

**被检查的函数**：`arch/riscv/kernel/machine_kexec.c`中的`machine_kexec_prepare`

**模型指出的问题**：控制页只用set_memory_x加上可执行权限，没有清除写权限，页面保持可写可执行（W+X）；x86参照实现用set_memory_rox设为只读可执行。

**真实修复的标题**：riscv: Prevent NULL pointer dereference in machine_kexec_prepare()

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/machine_kexec.c b/arch/riscv/kernel/machine_kexec.c
index 2306ce3e5f22..738df176ff6f 100644
--- a/arch/riscv/kernel/machine_kexec.c
+++ b/arch/riscv/kernel/machine_kexec.c
@@ -42,4 +42,7 @@ machine_kexec_prepare(struct kimage *image)
 			continue;
 
+		if (!image->segment[i].buf)
+			continue;
+
 		if (image->file_mode)
 			memcpy(&fdt, image->segment[i].buf, sizeof(fdt));
```

## G06（A344）

**被检查的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_misaligned`

**模型指出的问题**：缺少 instrumentation_begin()/instrumentation_end() 来包围实际陷阱处理逻辑

**真实修复的标题**：riscv: misaligned: enable IRQs while handling misaligned accesses

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/traps.c b/arch/riscv/kernel/traps.c
index b1d991c78a23..9c83848797a7 100644
--- a/arch/riscv/kernel/traps.c
+++ b/arch/riscv/kernel/traps.c
@@ -221,8 +221,10 @@ static void do_trap_misaligned(struct pt_regs *regs, enum misaligned_access_type
 	irqentry_state_t state;
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
 		irqentry_enter_from_user_mode(regs);
-	else
+		local_irq_enable();
+	} else {
 		state = irqentry_nmi_enter(regs);
+	}
 
 	if (misaligned_handler[type].handler(regs))
@@ -230,8 +232,10 @@ static void do_trap_misaligned(struct pt_regs *regs, enum misaligned_access_type
 			      misaligned_handler[type].type_str);
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
+		local_irq_disable();
 		irqentry_exit_to_user_mode(regs);
-	else
+	} else {
 		irqentry_nmi_exit(regs, state);
+	}
 }
 
```

## G07（A328）

**被检查的函数**：`arch/riscv/kernel/setup.c`中的`parse_dtb`

**模型指出的问题**：调用 early_init_dt_scan 时用 __pa(dtb_early_va) 计算 DTB 物理地址，但 dtb_early_va 是早期 fixmap 映射，__pa 并不适用；应直接传入 DTB 的物理地址。

**真实修复的标题**：riscv: Fix wrong usage of __pa() on a fixmap address

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/setup.c b/arch/riscv/kernel/setup.c
index 016b48fcd6f2..45010e71df86 100644
--- a/arch/riscv/kernel/setup.c
+++ b/arch/riscv/kernel/setup.c
@@ -228,5 +228,5 @@ static void __init parse_dtb(void)
 {
 	/* Early scan of device tree from init memory */
-	if (early_init_dt_scan(dtb_early_va, __pa(dtb_early_va))) {
+	if (early_init_dt_scan(dtb_early_va, dtb_early_pa)) {
 		const char *name = of_flat_dt_get_machine_name();
 
```

## G08（A393）

**被检查的函数**：`arch/riscv/kernel/machine_kexec.c`中的`machine_kexec_prepare`

**模型指出的问题**：非 crash kexec 路径缺少对卡在内核中的 CPU 的检查，应在处理镜像前调用 cpus_are_stuck_in_kernel() 并返回 -EBUSY。

**真实修复的标题**：riscv: Prevent NULL pointer dereference in machine_kexec_prepare()

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/machine_kexec.c b/arch/riscv/kernel/machine_kexec.c
index 2306ce3e5f22..738df176ff6f 100644
--- a/arch/riscv/kernel/machine_kexec.c
+++ b/arch/riscv/kernel/machine_kexec.c
@@ -42,4 +42,7 @@ machine_kexec_prepare(struct kimage *image)
 			continue;
 
+		if (!image->segment[i].buf)
+			continue;
+
 		if (image->file_mode)
 			memcpy(&fdt, image->segment[i].buf, sizeof(fdt));
```

## G09（A305）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`emit_atomic`

**模型指出的问题**：32 位 BPF_CMPXCHG 路径在 rv_lr_w 取回旧值后未对 r0 做 emit_zextw，返回旧值可能符号扩展而非零扩展。

**真实修复的标题**：riscv, bpf: make some atomic operations fully ordered

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index a46ec7fb4489..e51b291b5baa 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -505,24 +505,24 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_fetch_<op>(dst_reg + off16, src_reg) */
 	case BPF_ADD | BPF_FETCH:
-		emit(is64 ? rv_amoadd_d(rs, rs, rd, 0, 0) :
-		     rv_amoadd_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoadd_d(rs, rs, rd, 1, 1) :
+		     rv_amoadd_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_AND | BPF_FETCH:
-		emit(is64 ? rv_amoand_d(rs, rs, rd, 0, 0) :
-		     rv_amoand_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoand_d(rs, rs, rd, 1, 1) :
+		     rv_amoand_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_OR | BPF_FETCH:
-		emit(is64 ? rv_amoor_d(rs, rs, rd, 0, 0) :
-		     rv_amoor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoor_d(rs, rs, rd, 1, 1) :
+		     rv_amoor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_XOR | BPF_FETCH:
-		emit(is64 ? rv_amoxor_d(rs, rs, rd, 0, 0) :
-		     rv_amoxor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoxor_d(rs, rs, rd, 1, 1) :
+		     rv_amoxor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
@@ -530,6 +530,6 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_xchg(dst_reg + off16, src_reg); */
 	case BPF_XCHG:
-		emit(is64 ? rv_amoswap_d(rs, rs, rd, 0, 0) :
-		     rv_amoswap_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoswap_d(rs, rs, rd, 1, 1) :
+		     rv_amoswap_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
```

## G10（A387）

**被检查的函数**：`arch/riscv/kvm/vcpu.c`中的`kvm_arch_vcpu_ioctl_set_guest_debug`

**模型指出的问题**：未校验 dbg->control 中的无效/不支持的标志位，直接存入 vcpu->guest_debug，未对未知位返回 -EINVAL

**真实修复的标题**：RISC-V: KVM: Fix ebreak self test failure

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/vcpu.c b/arch/riscv/kvm/vcpu.c
index a73690eda84b..cf6e231e76e2 100644
--- a/arch/riscv/kvm/vcpu.c
+++ b/arch/riscv/kvm/vcpu.c
@@ -539,4 +539,5 @@ int kvm_arch_vcpu_ioctl_set_guest_debug(struct kvm_vcpu *vcpu,
 		vcpu->guest_debug = 0;
 
+	kvm_riscv_vcpu_config_guest_debug(vcpu);
 	return 0;
 }
```

## G11（A344）

**被检查的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_misaligned`

**模型指出的问题**：x86参照实现在irqentry_enter/exit之间用instrumentation_begin()/instrumentation_end()包住可插桩的处理代码，RISC-V的do_trap_misaligned在进入entry之后直接调用handler和do_trap_error，没有这对标注。

**真实修复的标题**：riscv: misaligned: enable IRQs while handling misaligned accesses

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/traps.c b/arch/riscv/kernel/traps.c
index b1d991c78a23..9c83848797a7 100644
--- a/arch/riscv/kernel/traps.c
+++ b/arch/riscv/kernel/traps.c
@@ -221,8 +221,10 @@ static void do_trap_misaligned(struct pt_regs *regs, enum misaligned_access_type
 	irqentry_state_t state;
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
 		irqentry_enter_from_user_mode(regs);
-	else
+		local_irq_enable();
+	} else {
 		state = irqentry_nmi_enter(regs);
+	}
 
 	if (misaligned_handler[type].handler(regs))
@@ -230,8 +232,10 @@ static void do_trap_misaligned(struct pt_regs *regs, enum misaligned_access_type
 			      misaligned_handler[type].type_str);
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
+		local_irq_disable();
 		irqentry_exit_to_user_mode(regs);
-	else
+	} else {
 		irqentry_nmi_exit(regs, state);
+	}
 }
 
```

## G12（A359）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：GPA上界检查使用 >=，把恰好到达GPA空间末尾的合法memslot也拒绝了；参照实现用 > （即 base_gfn+npages 可等于上限）

**真实修复的标题**：RISC-V: KVM: Remove automatic I/O mapping for VM_PFNMAP

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index 525fb5a330c0..58f5f3536ffd 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -172,5 +172,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 {
 	hva_t hva, reg_end, size;
-	gpa_t base_gpa;
 	bool writable;
 	int ret = 0;
@@ -191,5 +190,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	size = new->npages << PAGE_SHIFT;
 	reg_end = hva + size;
-	base_gpa = new->base_gfn << PAGE_SHIFT;
 	writable = !(new->flags & KVM_MEM_READONLY);
 
@@ -198,6 +196,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	/*
 	 * A memory region could potentially cover multiple VMAs, and
-	 * any holes between them, so iterate over all of them to find
-	 * out if we can map any of them right now.
+	 * any holes between them, so iterate over all of them.
 	 *
 	 *     +--------------------------------------------+
@@ -210,5 +207,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	do {
 		struct vm_area_struct *vma;
-		hva_t vm_start, vm_end;
+		hva_t vm_end;
 
 		vma = find_vma_intersection(current->mm, hva, reg_end);
@@ -226,14 +223,7 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 
 		/* Take the intersection of this VMA with the memory region */
-		vm_start = max(hva, vma->vm_start);
 		vm_end = min(reg_end, vma->vm_end);
 
 		if (vma->vm_flags & VM_PFNMAP) {
-			gpa_t gpa = base_gpa + (vm_start - hva);
-			phys_addr_t pa;
-
-			pa = (phys_addr_t)vma->vm_pgoff << PAGE_SHIFT;
-			pa += vm_start - vma->vm_start;
-
 			/* IO region dirty page logging not allowed */
 			if (new->flags & KVM_MEM_LOG_DIRTY_PAGES) {
@@ -241,19 +231,8 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 				goto out;
 			}
-
-			ret = kvm_riscv_mmu_ioremap(kvm, gpa, pa, vm_end - vm_start,
-						    writable, false);
-			if (ret)
-				break;
 		}
 		hva = vm_end;
 	} while (hva < reg_end);
 
-	if (change == KVM_MR_FLAGS_ONLY)
-		goto out;
-
-	if (ret)
-		kvm_riscv_mmu_iounmap(kvm, base_gpa, size);
-
 out:
 	mmap_read_unlock(current->mm);
```

## G13（A398）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：GPA范围上界检查使用了`>=`，应像arm64/x86那样允许区域末尾恰好等于GPA空间上限（用`>`），否则会错误拒绝刚好填满GPA空间末尾的合法memslot

**真实修复的标题**：RISC-V: KVM: Allow memslots ending at the GPA limit

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index d9040c394933..6035b5ec9503 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -273,5 +273,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	 * space addressable by the KVM guest GPA space.
 	 */
-	if ((new->base_gfn + new->npages) >=
+	if ((new->base_gfn + new->npages) >
 	     kvm_riscv_gstage_gpa_size(kvm->arch.pgd_levels) >> PAGE_SHIFT)
 		return -EFAULT;
```

## G14（A301）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`invoke_bpf_prog`

**模型指出的问题**：invoke_bpf_prog 的条件跳转占位符 rv_nop 位于保存 bpf_trampoline_enter 返回值到 S1 之前；当 enter 返回 0 触发跳转时会跳过 line733，随后 line759 用未初始化的 S1 调用 bpf_trampoline_exit。

**真实修复的标题**：riscv, bpf: Fix incorrect runtime stats

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index 1adf2f39ce59..ec9d692838fc 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -723,4 +723,7 @@ static int invoke_bpf_prog(struct bpf_tramp_link *l, int args_off, int retval_of
 		return ret;
 
+	/* store prog start time */
+	emit_mv(RV_REG_S1, RV_REG_A0, ctx);
+
 	/* if (__bpf_prog_enter(prog) == 0)
 	 *	goto skip_exec_of_prog;
@@ -730,7 +733,4 @@ static int invoke_bpf_prog(struct bpf_tramp_link *l, int args_off, int retval_of
 	emit(rv_nop(), ctx);
 
-	/* store prog start time */
-	emit_mv(RV_REG_S1, RV_REG_A0, ctx);
-
 	/* arg1: &args_off */
 	emit_addi(RV_REG_A0, RV_REG_FP, -args_off, ctx);
```

## G15（A387）

**被检查的函数**：`arch/riscv/kvm/vcpu.c`中的`kvm_arch_vcpu_ioctl_set_guest_debug`

**模型指出的问题**：RISC-V 未先校验 dbg->control 中是否包含 KVM_GUESTDBG_VALID_MASK 之外的无效标志并返回 -EINVAL。

**真实修复的标题**：RISC-V: KVM: Fix ebreak self test failure

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/vcpu.c b/arch/riscv/kvm/vcpu.c
index a73690eda84b..cf6e231e76e2 100644
--- a/arch/riscv/kvm/vcpu.c
+++ b/arch/riscv/kvm/vcpu.c
@@ -539,4 +539,5 @@ int kvm_arch_vcpu_ioctl_set_guest_debug(struct kvm_vcpu *vcpu,
 		vcpu->guest_debug = 0;
 
+	kvm_riscv_vcpu_config_guest_debug(vcpu);
 	return 0;
 }
```

## G16（A398）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：GPA 上界检查存在 off-by-one：应允许 base_gfn + npages 等于 GPA 页数上限，当前用 >= 会错误拒绝恰好结束于末尾的合法内存区域。

**真实修复的标题**：RISC-V: KVM: Allow memslots ending at the GPA limit

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index d9040c394933..6035b5ec9503 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -273,5 +273,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	 * space addressable by the KVM guest GPA space.
 	 */
-	if ((new->base_gfn + new->npages) >=
+	if ((new->base_gfn + new->npages) >
 	     kvm_riscv_gstage_gpa_size(kvm->arch.pgd_levels) >> PAGE_SHIFT)
 		return -EFAULT;
```

## G17（A288）

**被检查的函数**：`arch/riscv/kernel/module.c`中的`module_alloc`

**模型指出的问题**：RISC-V的module_alloc未调用kasan_alloc_module_shadow（及失败时vfree），若启用KASAN且模块区位于vmalloc区，模块内存缺少shadow映射，可能导致KASAN访问异常；另外也没有VM_FLUSH_RESET_PERMS等标志，权限重置情况不确定。

**真实修复的标题**：riscv: Fix module_alloc() that did not reset the linear mapping permissions

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/module.c b/arch/riscv/kernel/module.c
index aac019ed63b1..862834bb1d64 100644
--- a/arch/riscv/kernel/module.c
+++ b/arch/riscv/kernel/module.c
@@ -895,5 +895,6 @@ void *module_alloc(unsigned long size)
 	return __vmalloc_node_range(size, 1, MODULES_VADDR,
 				    MODULES_END, GFP_KERNEL,
-				    PAGE_KERNEL, 0, NUMA_NO_NODE,
+				    PAGE_KERNEL, VM_FLUSH_RESET_PERMS,
+				    NUMA_NO_NODE,
 				    __builtin_return_address(0));
 }
```

## G18（A301）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`invoke_bpf_prog`

**模型指出的问题**：RISC-V 在条件跳过分支之后才把 bpf_trampoline_enter 的返回值保存到 S1，导致 enter 返回 0 时 exit 收到陈旧起始时间。

**真实修复的标题**：riscv, bpf: Fix incorrect runtime stats

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index 1adf2f39ce59..ec9d692838fc 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -723,4 +723,7 @@ static int invoke_bpf_prog(struct bpf_tramp_link *l, int args_off, int retval_of
 		return ret;
 
+	/* store prog start time */
+	emit_mv(RV_REG_S1, RV_REG_A0, ctx);
+
 	/* if (__bpf_prog_enter(prog) == 0)
 	 *	goto skip_exec_of_prog;
@@ -730,7 +733,4 @@ static int invoke_bpf_prog(struct bpf_tramp_link *l, int args_off, int retval_of
 	emit(rv_nop(), ctx);
 
-	/* store prog start time */
-	emit_mv(RV_REG_S1, RV_REG_A0, ctx);
-
 	/* arg1: &args_off */
 	emit_addi(RV_REG_A0, RV_REG_FP, -args_off, ctx);
```

## G19（A313）

**被检查的函数**：`arch/riscv/mm/fault.c`中的`mm_fault_error`

**模型指出的问题**：RISC-V 的 mm_fault_error 缺少 __kprobes 标记

**真实修复的标题**：riscv/mm: Add handling for VM_FAULT_SIGSEGV in mm_fault_error()

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/mm/fault.c b/arch/riscv/mm/fault.c
index 5224f3733802..a9f2b4af8f3f 100644
--- a/arch/riscv/mm/fault.c
+++ b/arch/riscv/mm/fault.c
@@ -62,4 +62,9 @@ static inline void no_context(struct pt_regs *regs, unsigned long addr)
 static inline void mm_fault_error(struct pt_regs *regs, unsigned long addr, vm_fault_t fault)
 {
+	if (!user_mode(regs)) {
+		no_context(regs, addr);
+		return;
+	}
+
 	if (fault & VM_FAULT_OOM) {
 		/*
@@ -67,19 +72,15 @@ static inline void mm_fault_error(struct pt_regs *regs, unsigned long addr, vm_f
 		 * (which will retry the fault, or kill us if we got oom-killed).
 		 */
-		if (!user_mode(regs)) {
-			no_context(regs, addr);
-			return;
-		}
 		pagefault_out_of_memory();
 		return;
 	} else if (fault & (VM_FAULT_SIGBUS | VM_FAULT_HWPOISON | VM_FAULT_HWPOISON_LARGE)) {
 		/* Kernel mode? Handle exceptions or die */
-		if (!user_mode(regs)) {
-			no_context(regs, addr);
-			return;
-		}
 		do_trap(regs, SIGBUS, BUS_ADRERR, addr);
 		return;
+	} else if (fault & VM_FAULT_SIGSEGV) {
+		do_trap(regs, SIGSEGV, SEGV_MAPERR, addr);
+		return;
 	}
+
 	BUG();
 }
```

## G20（A321）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`emit_atomic`

**模型指出的问题**：32 位 BPF_CMPXCHG 的旧值返回没有零扩展，R0 会保留 rv_lr_w 的符号扩展值。

**真实修复的标题**：riscv, bpf: Make BPF_CMPXCHG fully ordered

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index 91bd5082c4d8..4cc631fa7039 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -551,6 +551,6 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 		jmp_offset = ninsns_rvoff(8);
 		emit(rv_bne(RV_REG_T2, r0, jmp_offset >> 1), ctx);
-		emit(is64 ? rv_sc_d(RV_REG_T3, rs, rd, 0, 0) :
-		     rv_sc_w(RV_REG_T3, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_sc_d(RV_REG_T3, rs, rd, 0, 1) :
+		     rv_sc_w(RV_REG_T3, rs, rd, 0, 1), ctx);
 		jmp_offset = ninsns_rvoff(-6);
 		emit(rv_bne(RV_REG_T3, 0, jmp_offset >> 1), ctx);
```

## G21（A327）

**被检查的函数**：`arch/riscv/kernel/jump_label.c`中的`arch_jump_label_transform_queue`

**模型指出的问题**：RISC-V在jump label补丁后仅调用patch_insn_write，未调用patch_text_nosync或flush_icache_range，缺少指令缓存同步/IPI，可能继续执行旧指令。

**真实修复的标题**：riscv: Fixup boot failure when CONFIG_DEBUG_RT_MUTEXES=y

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/jump_label.c b/arch/riscv/kernel/jump_label.c
index 6eee6f736f68..654ed159c830 100644
--- a/arch/riscv/kernel/jump_label.c
+++ b/arch/riscv/kernel/jump_label.c
@@ -37,7 +37,13 @@ bool arch_jump_label_transform_queue(struct jump_entry *entry,
 	}
 
-	mutex_lock(&text_mutex);
-	patch_insn_write(addr, &insn, sizeof(insn));
-	mutex_unlock(&text_mutex);
+	if (early_boot_irqs_disabled) {
+		riscv_patch_in_stop_machine = 1;
+		patch_insn_write(addr, &insn, sizeof(insn));
+		riscv_patch_in_stop_machine = 0;
+	} else {
+		mutex_lock(&text_mutex);
+		patch_insn_write(addr, &insn, sizeof(insn));
+		mutex_unlock(&text_mutex);
+	}
 
 	return true;
```

## G22（A288）

**被检查的函数**：`arch/riscv/kernel/module.c`中的`module_alloc`

**模型指出的问题**：module_alloc 分配模块内存后没有调用 kasan_alloc_module_shadow 为其建立 KASAN 影子内存，失败时也没有 vfree 并返回 NULL

**真实修复的标题**：riscv: Fix module_alloc() that did not reset the linear mapping permissions

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/module.c b/arch/riscv/kernel/module.c
index aac019ed63b1..862834bb1d64 100644
--- a/arch/riscv/kernel/module.c
+++ b/arch/riscv/kernel/module.c
@@ -895,5 +895,6 @@ void *module_alloc(unsigned long size)
 	return __vmalloc_node_range(size, 1, MODULES_VADDR,
 				    MODULES_END, GFP_KERNEL,
-				    PAGE_KERNEL, 0, NUMA_NO_NODE,
+				    PAGE_KERNEL, VM_FLUSH_RESET_PERMS,
+				    NUMA_NO_NODE,
 				    __builtin_return_address(0));
 }
```

## G23（A305）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`emit_atomic`

**模型指出的问题**：32 位 BPF_CMPXCHG 返回的旧值未按 eBPF 语义零扩展，rv_lr_w 的符号扩展高位会留在 r0。

**真实修复的标题**：riscv, bpf: make some atomic operations fully ordered

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index a46ec7fb4489..e51b291b5baa 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -505,24 +505,24 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_fetch_<op>(dst_reg + off16, src_reg) */
 	case BPF_ADD | BPF_FETCH:
-		emit(is64 ? rv_amoadd_d(rs, rs, rd, 0, 0) :
-		     rv_amoadd_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoadd_d(rs, rs, rd, 1, 1) :
+		     rv_amoadd_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_AND | BPF_FETCH:
-		emit(is64 ? rv_amoand_d(rs, rs, rd, 0, 0) :
-		     rv_amoand_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoand_d(rs, rs, rd, 1, 1) :
+		     rv_amoand_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_OR | BPF_FETCH:
-		emit(is64 ? rv_amoor_d(rs, rs, rd, 0, 0) :
-		     rv_amoor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoor_d(rs, rs, rd, 1, 1) :
+		     rv_amoor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_XOR | BPF_FETCH:
-		emit(is64 ? rv_amoxor_d(rs, rs, rd, 0, 0) :
-		     rv_amoxor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoxor_d(rs, rs, rd, 1, 1) :
+		     rv_amoxor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
@@ -530,6 +530,6 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_xchg(dst_reg + off16, src_reg); */
 	case BPF_XCHG:
-		emit(is64 ? rv_amoswap_d(rs, rs, rd, 0, 0) :
-		     rv_amoswap_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoswap_d(rs, rs, rd, 1, 1) :
+		     rv_amoswap_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
```

## G24（A288）

**被检查的函数**：`arch/riscv/kernel/module.c`中的`module_alloc`

**模型指出的问题**：RISC-V module_alloc 未为 KASAN 调用 kasan_alloc_module_shadow，也未在 shadow 分配失败时 vfree 清理。

**真实修复的标题**：riscv: Fix module_alloc() that did not reset the linear mapping permissions

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/module.c b/arch/riscv/kernel/module.c
index aac019ed63b1..862834bb1d64 100644
--- a/arch/riscv/kernel/module.c
+++ b/arch/riscv/kernel/module.c
@@ -895,5 +895,6 @@ void *module_alloc(unsigned long size)
 	return __vmalloc_node_range(size, 1, MODULES_VADDR,
 				    MODULES_END, GFP_KERNEL,
-				    PAGE_KERNEL, 0, NUMA_NO_NODE,
+				    PAGE_KERNEL, VM_FLUSH_RESET_PERMS,
+				    NUMA_NO_NODE,
 				    __builtin_return_address(0));
 }
```

## G25（A379）

**被检查的函数**：`arch/riscv/kernel/patch.c`中的`patch_map`

**模型指出的问题**：patch_map 对内核/exit text 仍通过 phys_to_page/page_to_phys 转换，未像 arm64 在映像文本分支直接使用 __pa_symbol 的物理地址，存在早期 page_to_phys 类问题。

**真实修复的标题**：riscv: patch: Avoid early phys_to_page()

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kernel/patch.c b/arch/riscv/kernel/patch.c
index db13c9ddf9e3..16b243376f36 100644
--- a/arch/riscv/kernel/patch.c
+++ b/arch/riscv/kernel/patch.c
@@ -43,17 +43,18 @@ static __always_inline void *patch_map(void *addr, const unsigned int fixmap)
 {
 	uintptr_t uintaddr = (uintptr_t) addr;
-	struct page *page;
+	phys_addr_t phys;
 
-	if (core_kernel_text(uintaddr) || is_kernel_exittext(uintaddr))
-		page = phys_to_page(__pa_symbol(addr));
-	else if (IS_ENABLED(CONFIG_STRICT_MODULE_RWX))
-		page = vmalloc_to_page(addr);
-	else
-		return addr;
+	if (core_kernel_text(uintaddr) || is_kernel_exittext(uintaddr)) {
+		phys = __pa_symbol(addr);
+	} else if (IS_ENABLED(CONFIG_STRICT_MODULE_RWX)) {
+		struct page *page = vmalloc_to_page(addr);
 
-	BUG_ON(!page);
+		BUG_ON(!page);
+		phys = page_to_phys(page) + offset_in_page(addr);
+	} else {
+		return addr;
+	}
 
-	return (void *)set_fixmap_offset(fixmap, page_to_phys(page) +
-					 offset_in_page(addr));
+	return (void *)set_fixmap_offset(fixmap, phys);
 }
 
```

## G26（A359）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：GPA 上界检查的等号处理错误：base_gfn + npages 是排他末端，等于 GPA 页数时仍合法，RISC-V 却拒绝了。

**真实修复的标题**：RISC-V: KVM: Remove automatic I/O mapping for VM_PFNMAP

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index 525fb5a330c0..58f5f3536ffd 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -172,5 +172,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 {
 	hva_t hva, reg_end, size;
-	gpa_t base_gpa;
 	bool writable;
 	int ret = 0;
@@ -191,5 +190,4 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	size = new->npages << PAGE_SHIFT;
 	reg_end = hva + size;
-	base_gpa = new->base_gfn << PAGE_SHIFT;
 	writable = !(new->flags & KVM_MEM_READONLY);
 
@@ -198,6 +196,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	/*
 	 * A memory region could potentially cover multiple VMAs, and
-	 * any holes between them, so iterate over all of them to find
-	 * out if we can map any of them right now.
+	 * any holes between them, so iterate over all of them.
 	 *
 	 *     +--------------------------------------------+
@@ -210,5 +207,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	do {
 		struct vm_area_struct *vma;
-		hva_t vm_start, vm_end;
+		hva_t vm_end;
 
 		vma = find_vma_intersection(current->mm, hva, reg_end);
@@ -226,14 +223,7 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 
 		/* Take the intersection of this VMA with the memory region */
-		vm_start = max(hva, vma->vm_start);
 		vm_end = min(reg_end, vma->vm_end);
 
 		if (vma->vm_flags & VM_PFNMAP) {
-			gpa_t gpa = base_gpa + (vm_start - hva);
-			phys_addr_t pa;
-
-			pa = (phys_addr_t)vma->vm_pgoff << PAGE_SHIFT;
-			pa += vm_start - vma->vm_start;
-
 			/* IO region dirty page logging not allowed */
 			if (new->flags & KVM_MEM_LOG_DIRTY_PAGES) {
@@ -241,19 +231,8 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 				goto out;
 			}
-
-			ret = kvm_riscv_mmu_ioremap(kvm, gpa, pa, vm_end - vm_start,
-						    writable, false);
-			if (ret)
-				break;
 		}
 		hva = vm_end;
 	} while (hva < reg_end);
 
-	if (change == KVM_MR_FLAGS_ONLY)
-		goto out;
-
-	if (ret)
-		kvm_riscv_mmu_iounmap(kvm, base_gpa, size);
-
 out:
 	mmap_read_unlock(current->mm);
```

## G27（A305）

**被检查的函数**：`arch/riscv/net/bpf_jit_comp64.c`中的`emit_atomic`

**模型指出的问题**：switch(imm)没有default分支，遇到未知的原子操作码时不报错、不返回错误，静默不生成任何指令（函数返回void，无法让JIT失败）

**真实修复的标题**：riscv, bpf: make some atomic operations fully ordered

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index a46ec7fb4489..e51b291b5baa 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -505,24 +505,24 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_fetch_<op>(dst_reg + off16, src_reg) */
 	case BPF_ADD | BPF_FETCH:
-		emit(is64 ? rv_amoadd_d(rs, rs, rd, 0, 0) :
-		     rv_amoadd_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoadd_d(rs, rs, rd, 1, 1) :
+		     rv_amoadd_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_AND | BPF_FETCH:
-		emit(is64 ? rv_amoand_d(rs, rs, rd, 0, 0) :
-		     rv_amoand_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoand_d(rs, rs, rd, 1, 1) :
+		     rv_amoand_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_OR | BPF_FETCH:
-		emit(is64 ? rv_amoor_d(rs, rs, rd, 0, 0) :
-		     rv_amoor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoor_d(rs, rs, rd, 1, 1) :
+		     rv_amoor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
 		break;
 	case BPF_XOR | BPF_FETCH:
-		emit(is64 ? rv_amoxor_d(rs, rs, rd, 0, 0) :
-		     rv_amoxor_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoxor_d(rs, rs, rd, 1, 1) :
+		     rv_amoxor_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
@@ -530,6 +530,6 @@ static void emit_atomic(u8 rd, u8 rs, s16 off, s32 imm, bool is64,
 	/* src_reg = atomic_xchg(dst_reg + off16, src_reg); */
 	case BPF_XCHG:
-		emit(is64 ? rv_amoswap_d(rs, rs, rd, 0, 0) :
-		     rv_amoswap_w(rs, rs, rd, 0, 0), ctx);
+		emit(is64 ? rv_amoswap_d(rs, rs, rd, 1, 1) :
+		     rv_amoswap_w(rs, rs, rd, 1, 1), ctx);
 		if (!is64)
 			emit_zextw(rs, rs, ctx);
```

## G28（A398）

**被检查的函数**：`arch/riscv/kvm/mmu.c`中的`kvm_arch_prepare_memory_region`

**模型指出的问题**：RISC-V 的 GPA 上界检查使用 >=，会把恰好结束于可寻址 GPA 上界的 memslot 误判为越界。

**真实修复的标题**：RISC-V: KVM: Allow memslots ending at the GPA limit

**真实修复对RISC-V的改动**：

```diff
diff --git a/arch/riscv/kvm/mmu.c b/arch/riscv/kvm/mmu.c
index d9040c394933..6035b5ec9503 100644
--- a/arch/riscv/kvm/mmu.c
+++ b/arch/riscv/kvm/mmu.c
@@ -273,5 +273,5 @@ int kvm_arch_prepare_memory_region(struct kvm *kvm,
 	 * space addressable by the KVM guest GPA space.
 	 */
-	if ((new->base_gfn + new->npages) >=
+	if ((new->base_gfn + new->npages) >
 	     kvm_riscv_gstage_gpa_size(kvm->arch.pgd_levels) >> PAGE_SHIFT)
 		return -EFAULT;
```
