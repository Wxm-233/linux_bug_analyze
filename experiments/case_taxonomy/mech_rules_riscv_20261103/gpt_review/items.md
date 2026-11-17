# 待复核的标记（Linux v6.6）

## Q00

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`kernel/trace/ftrace.c`中的`arch_ftrace_update_code`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 2943  {
 2944  	ftrace_run_stop_machine(command);
 2945  }
```

## Q01

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`drivers/pci/probe.c`中的`pcibios_root_bridge_prepare`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 3029  {
 3030  	return 0;
 3031  }
```

## Q02

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/asm-generic/io.h`中的`memcpy_fromio`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 1183  {
 1184  	memcpy(buffer, __io_virt(addr), size);
 1185  }
```

## Q03

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/linux/ftrace.h`中的`ftrace_graph_func`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
  907  #ifndef ftrace_graph_func
  908  #define ftrace_graph_func ftrace_stub
  909  #define FTRACE_OPS_GRAPH_STUB FTRACE_OPS_FL_STUB
  910  #else
  911  #define FTRACE_OPS_GRAPH_STUB 0
  912  #endif
```

## Q04

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/asm-generic/io.h`中的`memcpy_toio`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 1200  {
 1201  	memcpy(__io_virt(addr), buffer, size);
 1202  }
```

## Q05

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`drivers/pci/probe.c`中的`pcibios_add_bus`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 3034  {
 3035  }
```

## Q06

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`mm/sparse-vmemmap.c`中的`vmemmap_set_pmd`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
  300  {
  301  }
```

## Q07

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/asm-generic/pci.h`中的`pcibios_assign_all_busses`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
   14  #ifndef pcibios_assign_all_busses
   15  /* For bootloaders that do not initialize the PCI bus */
   16  #define pcibios_assign_all_busses() 1
   17  #endif
```

## Q08

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/asm-generic/io.h`中的`ioremap_wc`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
 1068  #ifndef ioremap_wc
 1069  #define ioremap_wc ioremap
 1070  #endif
```

## Q09

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`drivers/base/cacheinfo.c`中的`init_cache_level`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
  472  {
  473  	return -ENOENT;
  474  }
```

## Q10

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`mm/sparse-vmemmap.c`中的`vmemmap_check_pmd`

**程序给出的理由**：weak default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
  305  {
  306  	return 0;
  307  }
```

## Q11

**规则**：公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。

**位置**：`include/asm-generic/mmu_context.h`中的`enter_lazy_tlb`

**程序给出的理由**：ifndef default overridden by arm64, x86 and loongarch, not by riscv

**代码**：

```c
   23  {
   24  }
```

## Q12

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_write_target`

**程序给出的理由**：line 100: [irq] after bound check at line 98, no array_index_nospec

**代码**：

```c
   94  {
   95  	unsigned long flags;
   96  	struct aplic_irq *irqd;
   97  
   98  	if (!irq || aplic->nr_irqs <= irq)
   99  		return;
  100  	irqd = &aplic->irqs[irq];
  101  
  102  	val &= APLIC_TARGET_EIID_MASK |
  103  	       (APLIC_TARGET_HART_IDX_MASK << APLIC_TARGET_HART_IDX_SHIFT) |
  104  	       (APLIC_TARGET_GUEST_IDX_MASK << APLIC_TARGET_GUEST_IDX_SHIFT);
  105  
  106  	raw_spin_lock_irqsave(&irqd->lock, flags);
  107  	irqd->target = val;
  108  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  109  }
```

## Q13

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_incr_fw`

**程序给出的理由**：line 271: [fid] after bound check at line 268, no array_index_nospec

**代码**：

```c
  264  {
  265  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  266  	struct kvm_fw_event *fevent;
  267  
  268  	if (!kvpmu || fid >= SBI_PMU_FW_MAX)
  269  		return -EINVAL;
  270  
  271  	fevent = &kvpmu->fw_event[fid];
  272  	if (fevent->started)
  273  		fevent->value++;
  274  
  275  	return 0;
  276  }
```

## Q14

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_cfg_match`

**程序给出的理由**：line 512: [ctr_idx] after bound check at line 506, no array_index_nospec; line 517: [event_code] after bound check at line 489, no array_index_nospec

**代码**：

```c
  460  {
  461  	int ctr_idx, ret, sbiret = 0;
  462  	bool is_fevent;
  463  	unsigned long event_code;
  464  	u32 etype = kvm_pmu_get_perf_event_type(eidx);
  465  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  466  	struct kvm_pmc *pmc = NULL;
  467  	struct perf_event_attr attr = {
  468  		.type = etype,
  469  		.size = sizeof(struct perf_event_attr),
  470  		.pinned = true,
  471  		/*
  472  		 * It should never reach here if the platform doesn't support the sscofpmf
  473  		 * extension as mode filtering won't work without it.
  474  		 */
  475  		.exclude_host = true,
  476  		.exclude_hv = true,
  477  		.exclude_user = !!(flags & SBI_PMU_CFG_FLAG_SET_UINH),
  478  		.exclude_kernel = !!(flags & SBI_PMU_CFG_FLAG_SET_SINH),
  479  		.config1 = RISCV_PMU_CONFIG1_GUEST_EVENTS,
  480  	};
  481  
  482  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  483  		sbiret = SBI_ERR_INVALID_PARAM;
  484  		goto out;
  485  	}
  486  
  487  	event_code = get_event_code(eidx);
  488  	is_fevent = kvm_pmu_is_fw_event(eidx);
  489  	if (is_fevent && event_code >= SBI_PMU_FW_MAX) {
  490  		sbiret = SBI_ERR_NOT_SUPPORTED;
  491  		goto out;
  492  	}
  493  
  494  	/*
  495  	 * SKIP_MATCH flag indicates the caller is aware of the assigned counter
  496  	 * for this event. Just do a sanity check if it already marked used.
  497  	 */
  498  	if (flags & SBI_PMU_CFG_FLAG_SKIP_MATCH) {
  499  		if (!test_bit(ctr_base + __ffs(ctr_mask), kvpmu->pmc_in_use)) {
  500  			sbiret = SBI_ERR_FAILURE;
  501  			goto out;
  502  		}
  503  		ctr_idx = ctr_base + __ffs(ctr_mask);
  504  	} else  {
  505  		ctr_idx = pmu_get_pmc_index(kvpmu, eidx, ctr_base, ctr_mask);
  506  		if (ctr_idx < 0) {
  507  			sbiret = SBI_ERR_NOT_SUPPORTED;
  508  			goto out;
  509  		}
  510  	}
  511  
  512  	pmc = &kvpmu->pmc[ctr_idx];
  513  	pmc->idx = ctr_idx;
  514  
  515  	if (is_fevent) {
  516  		if (flags & SBI_PMU_CFG_FLAG_AUTO_START)
  517  			kvpmu->fw_event[event_code].started = true;
  518  	} else {
  519  		ret = kvm_pmu_create_perf_event(pmc, &attr, flags, eidx, evtdata);
  520  		if (ret)
  521  			return ret;
  522  	}
  523  
  524  	set_bit(ctr_idx, kvpmu->pmc_in_use);
  525  	pmc->event_idx = eidx;
  526  	retdata->out_val = ctr_idx;
  527  out:
  528  	retdata->err_val = sbiret;
  529  
  530  	return 0;
```

## Q15

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_read_input`

**程序给出的理由**：line 196: [irq] after bound check at line 194, no array_index_nospec

**代码**：

```c
  189  {
  190  	bool ret;
  191  	unsigned long flags;
  192  	struct aplic_irq *irqd;
  193  
  194  	if (!irq || aplic->nr_irqs <= irq)
  195  		return false;
  196  	irqd = &aplic->irqs[irq];
  197  
  198  	raw_spin_lock_irqsave(&irqd->lock, flags);
  199  	ret = (irqd->state & APLIC_IRQ_STATE_INPUT) ? true : false;
  200  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  201  
  202  	return ret;
  203  }
```

## Q16

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_read_target`

**程序给出的理由**：line 84: [irq] after bound check at line 82, no array_index_nospec

**代码**：

```c
   77  {
   78  	u32 ret;
   79  	unsigned long flags;
   80  	struct aplic_irq *irqd;
   81  
   82  	if (!irq || aplic->nr_irqs <= irq)
   83  		return 0;
   84  	irqd = &aplic->irqs[irq];
   85  
   86  	raw_spin_lock_irqsave(&irqd->lock, flags);
   87  	ret = irqd->target;
   88  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
   89  
   90  	return ret;
   91  }
```

## Q17

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_stop`

**程序给出的理由**：line 422: [fevent_code] after bound check at line 417, no array_index_nospec; line 425: [fevent_code] after bound check at line 417, no array_index_nospec

**代码**：

```c
  397  {
  398  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  399  	int i, pmc_index, sbiret = 0;
  400  	u64 enabled, running;
  401  	struct kvm_pmc *pmc;
  402  	int fevent_code;
  403  
  404  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  405  		sbiret = SBI_ERR_INVALID_PARAM;
  406  		goto out;
  407  	}
  408  
  409  	/* Stop the counters that have been configured and requested by the guest */
  410  	for_each_set_bit(i, &ctr_mask, RISCV_MAX_COUNTERS) {
  411  		pmc_index = i + ctr_base;
  412  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  413  			continue;
  414  		pmc = &kvpmu->pmc[pmc_index];
  415  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  416  			fevent_code = get_event_code(pmc->event_idx);
  417  			if (fevent_code >= SBI_PMU_FW_MAX) {
  418  				sbiret = SBI_ERR_INVALID_PARAM;
  419  				goto out;
  420  			}
  421  
  422  			if (!kvpmu->fw_event[fevent_code].started)
  423  				sbiret = SBI_ERR_ALREADY_STOPPED;
  424  
  425  			kvpmu->fw_event[fevent_code].started = false;
  426  		} else if (pmc->perf_event) {
  427  			if (pmc->started) {
  428  				/* Stop counting the counter */
  429  				perf_event_disable(pmc->perf_event);
  430  				pmc->started = false;
  431  			} else {
  432  				sbiret = SBI_ERR_ALREADY_STOPPED;
  433  			}
  434  
  435  			if (flags & SBI_PMU_STOP_FLAG_RESET) {
  436  				/* Relase the counter if this is a reset request */
  437  				pmc->counter_val += perf_event_read_value(pmc->perf_event,
  438  									  &enabled, &running);
  439  				kvm_pmu_release_perf_event(pmc);
  440  			}
  441  		} else {
  442  			sbiret = SBI_ERR_INVALID_PARAM;
  443  		}
  444  		if (flags & SBI_PMU_STOP_FLAG_RESET) {
  445  			pmc->event_idx = SBI_PMU_EVENT_IDX_INVALID;
  446  			clear_bit(pmc_index, kvpmu->pmc_in_use);
  447  		}
  448  	}
  449  
  450  out:
  451  	retdata->err_val = sbiret;
  452  
  453  	return 0;
  454  }
```

## Q18

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_write_enabled`

**程序给出的理由**：line 178: [irq] after bound check at line 176, no array_index_nospec

**代码**：

```c
  172  {
  173  	unsigned long flags;
  174  	struct aplic_irq *irqd;
  175  
  176  	if (!irq || aplic->nr_irqs <= irq)
  177  		return;
  178  	irqd = &aplic->irqs[irq];
  179  
  180  	raw_spin_lock_irqsave(&irqd->lock, flags);
  181  	if (enabled)
  182  		irqd->state |= APLIC_IRQ_STATE_ENABLED;
  183  	else
  184  		irqd->state &= ~APLIC_IRQ_STATE_ENABLED;
  185  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  186  }
```

## Q19

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_write_sourcecfg`

**程序给出的理由**：line 64: [irq] after bound check at line 62, no array_index_nospec

**代码**：

```c
   58  {
   59  	unsigned long flags;
   60  	struct aplic_irq *irqd;
   61  
   62  	if (!irq || aplic->nr_irqs <= irq)
   63  		return;
   64  	irqd = &aplic->irqs[irq];
   65  
   66  	if (val & APLIC_SOURCECFG_D)
   67  		val = 0;
   68  	else
   69  		val &= APLIC_SOURCECFG_SM_MASK;
   70  
   71  	raw_spin_lock_irqsave(&irqd->lock, flags);
   72  	irqd->sourcecfg = val;
   73  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
   74  }
```

## Q20

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kernel/kgdb.c`中的`dbg_set_reg`

**程序给出的理由**：line 225: [regno] after bound check at line 222, no array_index_nospec; line 226: [regno] after bound check at line 222, no array_index_nospec; line 227: [regno] after bound check at line 222, no array_index_nospec

**代码**：

```c
  221  {
  222  	if (regno >= DBG_MAX_REG_NUM || regno < 0)
  223  		return -EINVAL;
  224  
  225  	if (dbg_reg_def[regno].offset != -1)
  226  		memcpy((void *)regs + dbg_reg_def[regno].offset, mem,
  227  		       dbg_reg_def[regno].size);
  228  	return 0;
  229  }
```

## Q21

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/vcpu_onereg.c`中的`riscv_vcpu_set_isa_ext_single`

**程序给出的理由**：line 484: [reg_num] after bound check at line 480, no array_index_nospec

**代码**：

```c
  477  {
  478  	unsigned long host_isa_ext;
  479  
  480  	if (reg_num >= KVM_RISCV_ISA_EXT_MAX ||
  481  	    reg_num >= ARRAY_SIZE(kvm_isa_ext_arr))
  482  		return -ENOENT;
  483  
  484  	host_isa_ext = kvm_isa_ext_arr[reg_num];
  485  	if (!__riscv_isa_extension_available(NULL, host_isa_ext))
  486  		return -ENOENT;
  487  
  488  	if (reg_val == test_bit(host_isa_ext, vcpu->arch.isa))
  489  		return 0;
  490  
  491  	if (!vcpu->arch.ran_atleast_once) {
  492  		/*
  493  		 * All multi-letter extension and a few single letter
  494  		 * extension can be disabled
  495  		 */
  496  		if (reg_val == 1 &&
  497  		    kvm_riscv_vcpu_isa_enable_allowed(reg_num))
  498  			set_bit(host_isa_ext, vcpu->arch.isa);
  499  		else if (!reg_val &&
  500  			 kvm_riscv_vcpu_isa_disable_allowed(reg_num))
  501  			clear_bit(host_isa_ext, vcpu->arch.isa);
  502  		else
  503  			return -EINVAL;
  504  		kvm_riscv_vcpu_fp_reset(vcpu);
  505  	} else {
  506  		return -EBUSY;
  507  	}
  508  
  509  	return 0;
  510  }
```

## Q22

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_start`

**程序给出的理由**：line 368: [fevent_code] after bound check at line 362, no array_index_nospec; line 373: [fevent_code] after bound check at line 362, no array_index_nospec; line 374: [fevent_code] after bound check at line 362, no array_index_nospec

**代码**：

```c
  341  {
  342  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  343  	int i, pmc_index, sbiret = 0;
  344  	struct kvm_pmc *pmc;
  345  	int fevent_code;
  346  
  347  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  348  		sbiret = SBI_ERR_INVALID_PARAM;
  349  		goto out;
  350  	}
  351  
  352  	/* Start the counters that have been configured and requested by the guest */
  353  	for_each_set_bit(i, &ctr_mask, RISCV_MAX_COUNTERS) {
  354  		pmc_index = i + ctr_base;
  355  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  356  			continue;
  357  		pmc = &kvpmu->pmc[pmc_index];
  358  		if (flags & SBI_PMU_START_FLAG_SET_INIT_VALUE)
  359  			pmc->counter_val = ival;
  360  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  361  			fevent_code = get_event_code(pmc->event_idx);
  362  			if (fevent_code >= SBI_PMU_FW_MAX) {
  363  				sbiret = SBI_ERR_INVALID_PARAM;
  364  				goto out;
  365  			}
  366  
  367  			/* Check if the counter was already started for some reason */
  368  			if (kvpmu->fw_event[fevent_code].started) {
  369  				sbiret = SBI_ERR_ALREADY_STARTED;
  370  				continue;
  371  			}
  372  
  373  			kvpmu->fw_event[fevent_code].started = true;
  374  			kvpmu->fw_event[fevent_code].value = pmc->counter_val;
  375  		} else if (pmc->perf_event) {
  376  			if (unlikely(pmc->started)) {
  377  				sbiret = SBI_ERR_ALREADY_STARTED;
  378  				continue;
  379  			}
  380  			perf_event_period(pmc->perf_event, kvm_pmu_get_sample_period(pmc));
  381  			perf_event_enable(pmc->perf_event);
  382  			pmc->started = true;
  383  		} else {
  384  			sbiret = SBI_ERR_INVALID_PARAM;
  385  		}
  386  	}
  387  
  388  out:
  389  	retdata->err_val = sbiret;
  390  
  391  	return 0;
  392  }
```

## Q23

**规则**：函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。

**位置**：`arch/riscv/kvm/aia_aplic.c`中的`aplic_read_enabled`

**程序给出的理由**：line 162: [irq] after bound check at line 160, no array_index_nospec

**代码**：

```c
  155  {
  156  	bool ret;
  157  	unsigned long flags;
  158  	struct aplic_irq *irqd;
  159  
  160  	if (!irq || aplic->nr_irqs <= irq)
  161  		return false;
  162  	irqd = &aplic->irqs[irq];
  163  
  164  	raw_spin_lock_irqsave(&irqd->lock, flags);
  165  	ret = (irqd->state & APLIC_IRQ_STATE_ENABLED) ? true : false;
  166  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  167  
  168  	return ret;
  169  }
```

## Q24

**规则**：参照架构的一次修复删掉了某一行写法，而RISC-V同名函数中还保留着完全相同的一行。问题是：参照修掉的问题，RISC-V是否同样存在。

**位置**：`arch/riscv/kvm/mmu.c`中的`kvm_age_gfn`

**程序给出的理由**：df6556adf27b in arch/arm64/kvm/mmu.c removed "WARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);", still in riscv; added ['kvm_pgtable_stage2_test_clear_young', 'mmu', 'pgt']

**代码**：

```c
  574  {
  575  	pte_t *ptep;
  576  	u32 ptep_level = 0;
  577  	u64 size = (range->end - range->start) << PAGE_SHIFT;
  578  
  579  	if (!kvm->arch.pgd)
  580  		return false;
  581  
  582  	WARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);
  583  
  584  	if (!gstage_get_leaf_entry(kvm, range->start << PAGE_SHIFT,
  585  				   &ptep, &ptep_level))
  586  		return false;
  587  
  588  	return ptep_test_and_clear_young(NULL, 0, ptep);
  589  }
```

## Q25

**规则**：参照架构的一次修复删掉了某一行写法，而RISC-V同名函数中还保留着完全相同的一行。问题是：参照修掉的问题，RISC-V是否同样存在。

**位置**：`arch/riscv/include/asm/pgtable.h`中的`pud_user_accessible_page`

**程序给出的理由**：730a11f982e6 in arch/arm64/include/asm/pgtable.h removed "return pud_leaf(pud) && pud_user(pud);", still in riscv; added ['pud_user_exec']

**代码**：

```c
  747  {
  748  	return pud_leaf(pud) && pud_user(pud);
  749  }
```

## Q26

**规则**：参照架构的一次修复删掉了某一行写法，而RISC-V同名函数中还保留着完全相同的一行。问题是：参照修掉的问题，RISC-V是否同样存在。

**位置**：`arch/riscv/net/bpf_jit_core.c`中的`bpf_jit_alloc_exec`

**程序给出的理由**：b89ddf4cca43 in arch/arm64/net/bpf_jit_comp.c removed "return __vmalloc_node_range(size, PAGE_SIZE, BPF_JIT_REGION_START,", still in riscv; added ['vmalloc']

**代码**：

```c
  222  {
  223  	return __vmalloc_node_range(size, PAGE_SIZE, BPF_JIT_REGION_START,
  224  				    BPF_JIT_REGION_END, GFP_KERNEL,
  225  				    PAGE_KERNEL, 0, NUMA_NO_NODE,
  226  				    __builtin_return_address(0));
  227  }
```

## Q27

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/acpi.c`中的`__acpi_map_table`

**程序给出的理由**：all three references call ['early_memremap'], riscv does not

**代码**：

```c
  203  {
  204  	if (!size)
  205  		return NULL;
  206  
  207  	return early_ioremap(phys, size);
  208  }
```

## Q28

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/acpi.c`中的`__acpi_unmap_table`

**程序给出的理由**：all three references call ['early_memunmap'], riscv does not

**代码**：

```c
  211  {
  212  	if (!map || !size)
  213  		return;
  214  
  215  	early_iounmap(map, size);
  216  }
```

## Q29

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/process.c`中的`flush_thread`

**程序给出的理由**：all three references call ['flush_ptrace_hw_breakpoint'], riscv does not

**代码**：

```c
  140  {
  141  #ifdef CONFIG_FPU
  142  	/*
  143  	 * Reset FPU state and context
  144  	 *	frm: round to nearest, ties to even (IEEE default)
  145  	 *	fflags: accrued exceptions cleared
  146  	 */
  147  	fstate_off(current, task_pt_regs(current));
  148  	memset(&current->thread.fstate, 0, sizeof(current->thread.fstate));
  149  #endif
  150  #ifdef CONFIG_RISCV_ISA_V
  151  	/* Reset vector state */
  152  	riscv_v_vstate_ctrl_init(current);
  153  	riscv_v_vstate_off(task_pt_regs(current));
  154  	kfree(current->thread.vstate.datap);
  155  	memset(&current->thread.vstate, 0, sizeof(struct __riscv_v_ext_state));
  156  #endif
  157  }
```

## Q30

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/acpi.c`中的`pci_acpi_scan_root`

**程序给出的理由**：all three references call ['acpi_pci_root_create', 'pcie_bus_configure_settings'], riscv does not

**代码**：

```c
  248  {
  249  	return NULL;
  250  }
```

## Q31

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/acpi.c`中的`raw_pci_read`

**程序给出的理由**：all three references call ['read'], riscv does not

**代码**：

```c
  232  {
  233  	return PCIBIOS_DEVICE_NOT_FOUND;
  234  }
```

## Q32

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/kernel/acpi.c`中的`raw_pci_write`

**程序给出的理由**：all three references call ['write'], riscv does not

**代码**：

```c
  238  {
  239  	return PCIBIOS_DEVICE_NOT_FOUND;
  240  }
```

## Q33

**规则**：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。

**位置**：`arch/riscv/mm/init.c`中的`vmemmap_populate`

**程序给出的理由**：all three references call ['vmemmap_populate_hugepages'], riscv does not

**代码**：

```c
 1505  {
 1506  	return vmemmap_populate_basepages(start, end, node, NULL);
 1507  }
```
