# 待复核条目

## H01（A288）

**被检查的函数**：`arch/riscv/kernel/module.c`中的`module_alloc`

**模型指出的问题**：module_alloc分配成功后没有调用kasan_alloc_module_shadow为模块区域建立KASAN影子内存，直接返回；x86和arm64都做了此步并在失败时vfree返回NULL

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

## H02（A387）

**被检查的函数**：`arch/riscv/kvm/vcpu.c`中的`kvm_arch_vcpu_ioctl_set_guest_debug`

**模型指出的问题**：未校验dbg->control中的未知/不支持标志位，arm64会对这类位返回-EINVAL，RISC-V直接全部接受

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
