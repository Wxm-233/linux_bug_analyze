# evcard 审查材料（两榜前 12 条合并，打乱、隐去来源和名次）

判断：完整线索（公共代码的依赖、架构条件改变保证的依据、同一对象到消费者的证据，且已排除最直接的合法解释）/ 未决 / 排除 / 未知。
排除请写原因类别。行号前的 `>` 标出报告行。

## [1] WT（类型一致性）`arch/x86/kernel/tsc.c:1489` 函数 `get_loops_per_jiffy`
- 原始特征：`A|return:return|lpj`
- 卡片：消费位置 **有**（return:return（arch/x86/kernel/tsc.c:1489））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
```c
  1464  	if (tsc_khz == 0)
  1465  		tsc_khz = cpu_khz;
  1466  	else if (abs(cpu_khz - tsc_khz) * 10 > tsc_khz)
  1467  		cpu_khz = tsc_khz;
  1468  
  1469  	if (tsc_khz == 0)
  1470  		return false;
  1471  
  1472  	pr_info("Detected %lu.%03lu MHz processor\n",
  1473  		(unsigned long)cpu_khz / KHZ,
  1474  		(unsigned long)cpu_khz % KHZ);
  1475  
  1476  	if (cpu_khz != tsc_khz) {
  1477  		pr_info("Detected %lu.%03lu MHz TSC",
  1478  			(unsigned long)tsc_khz / KHZ,
  1479  			(unsigned long)tsc_khz % KHZ);
  1480  	}
  1481  	return true;
  1482  }
  1483  
  1484  static unsigned long __init get_loops_per_jiffy(void)
  1485  {
  1486  	u64 lpj = (u64)tsc_khz * KHZ;
  1487  
  1488  	do_div(lpj, HZ);
  1489> 	return lpj;
  1490  }
  1491  
  1492  static void __init tsc_enable_sched_clock(void)
  1493  {
  1494  	loops_per_jiffy = get_loops_per_jiffy();
  1495  	use_tsc_delay();
  1496  
  1497  	/* Sanitize TSC ADJUST before cyc2ns gets initialized */
  1498  	tsc_store_and_check_tsc_adjust(true);
  1499  	cyc2ns_init_boot_cpu();
  1500  	static_branch_enable(&__use_tsc);
  1501  }
  1502  
  1503  void __init tsc_early_init(void)
  1504  {
  1505  	if (!boot_cpu_has(X86_FEATURE_TSC))
  1506  		return;
  1507  	/* Don't change UV TSC multi-chassis synchronization */
  1508  	if (is_early_uv_system())
```

## [2] ORD（类型一致性）`mm/swap_table.h:314` 函数 `__swap_cgroup_set`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 -；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   289  	VM_WARN_ON(!swp_tb_is_countable(swp_tb));
   290  	return !!(swp_tb & SWP_TB_ZERO_FLAG);
   291  #else
   292  	return test_bit(ci_off, ci->zero_bitmap);
   293  #endif
   294  }
   295  
   296  static inline void __swap_table_clear_zero(struct swap_cluster_info *ci,
   297  					   unsigned int ci_off)
   298  {
   299  #if SWAP_TABLE_HAS_ZEROFLAG
   300  	unsigned long swp_tb = __swap_table_get(ci, ci_off);
   301  
   302  	VM_WARN_ON(!swp_tb_is_countable(swp_tb));
   303  	swp_tb &= ~SWP_TB_ZERO_FLAG;
   304  	__swap_table_set(ci, ci_off, swp_tb);
   305  #else
   306  	lockdep_assert_held(&ci->lock);
   307  	__clear_bit(ci_off, ci->zero_bitmap);
   308  #endif
   309  }
   310  
   311  #ifdef CONFIG_MEMCG
   312  static inline void __swap_cgroup_set(struct swap_cluster_info *ci,
   313  		unsigned int ci_off, unsigned long nr, unsigned short id)
   314> {
   315  	lockdep_assert_held(&ci->lock);
   316  	VM_WARN_ON_ONCE(ci_off >= SWAPFILE_CLUSTER);
   317  	if (WARN_ON_ONCE(!ci->memcg_table))
   318  		return;
   319  	do {
   320  		ci->memcg_table->id[ci_off++] = id;
   321  	} while (--nr);
   322  }
   323  
   324  static inline unsigned short __swap_cgroup_get(struct swap_cluster_info *ci,
   325  					       unsigned int ci_off)
   326  {
   327  	lockdep_assert_held(&ci->lock);
   328  	VM_WARN_ON_ONCE(ci_off >= SWAPFILE_CLUSTER);
   329  	if (unlikely(!ci->memcg_table))
   330  		return 0;
   331  	return ci->memcg_table->id[ci_off];
   332  }
   333  
```

## [3] ORD（类型一致性）`mm/swap_table.h:253` 函数 `swap_table_get`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 -；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   228  
   229  static inline unsigned long __swap_table_xchg(struct swap_cluster_info *ci,
   230  					      unsigned int off, unsigned long swp_tb)
   231  {
   232  	atomic_long_t *table = rcu_dereference_protected(ci->table, true);
   233  
   234  	lockdep_assert_held(&ci->lock);
   235  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   236  	/* Ordering is guaranteed by cluster lock, relax */
   237  	return atomic_long_xchg_relaxed(&table[off], swp_tb);
   238  }
   239  
   240  static inline unsigned long __swap_table_get(struct swap_cluster_info *ci,
   241  					     unsigned int off)
   242  {
   243  	atomic_long_t *table;
   244  
   245  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   246  	table = rcu_dereference_check(ci->table, lockdep_is_held(&ci->lock));
   247  
   248  	return atomic_long_read(&table[off]);
   249  }
   250  
   251  static inline unsigned long swap_table_get(struct swap_cluster_info *ci,
   252  					unsigned int off)
   253> {
   254  	atomic_long_t *table;
   255  	unsigned long swp_tb;
   256  
   257  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   258  
   259  	rcu_read_lock();
   260  	table = rcu_dereference(ci->table);
   261  	swp_tb = table ? atomic_long_read(&table[off]) : null_to_swp_tb();
   262  	rcu_read_unlock();
   263  
   264  	return swp_tb;
   265  }
   266  
   267  static inline void __swap_table_set_zero(struct swap_cluster_info *ci,
   268  					 unsigned int ci_off)
   269  {
   270  #if SWAP_TABLE_HAS_ZEROFLAG
   271  	unsigned long swp_tb = __swap_table_get(ci, ci_off);
   272  
```

## [4] WT（类型一致性）`arch/riscv/kernel/traps_misaligned.c:50` 函数 `set_f64_rd`
- 原始特征：`A|assign:value|val`
- 卡片：消费位置 **有**（assign:value（arch/riscv/kernel/traps_misaligned.c:50））；编入 r；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
```c
    25  #define FP_GET_RD(insn)		(insn >> 7 & 0x1F)
    26  
    27  extern void put_f32_reg(unsigned long fp_reg, unsigned long value);
    28  
    29  static int set_f32_rd(unsigned long insn, struct pt_regs *regs,
    30  		      unsigned long val)
    31  {
    32  	unsigned long fp_reg = FP_GET_RD(insn);
    33  
    34  	put_f32_reg(fp_reg, val);
    35  	regs->status |= SR_FS_DIRTY;
    36  
    37  	return 0;
    38  }
    39  
    40  extern void put_f64_reg(unsigned long fp_reg, unsigned long value);
    41  
    42  static int set_f64_rd(unsigned long insn, struct pt_regs *regs, u64 val)
    43  {
    44  	unsigned long fp_reg = FP_GET_RD(insn);
    45  	unsigned long value;
    46  
    47  #if __riscv_xlen == 32
    48  	value = (unsigned long) &val;
    49  #else
    50> 	value = val;
    51  #endif
    52  	put_f64_reg(fp_reg, value);
    53  	regs->status |= SR_FS_DIRTY;
    54  
    55  	return 0;
    56  }
    57  
    58  #if __riscv_xlen == 32
    59  extern void get_f64_reg(unsigned long fp_reg, u64 *value);
    60  
    61  static u64 get_f64_rs(unsigned long insn, u8 fp_reg_offset,
    62  		      struct pt_regs *regs)
    63  {
    64  	unsigned long fp_reg = (insn >> fp_reg_offset) & 0x1F;
    65  	u64 val;
    66  
    67  	get_f64_reg(fp_reg, &val);
    68  	regs->status |= SR_FS_DIRTY;
    69  
```

## [5] ORD（类型一致性）`mm/swapfile.c:967` 函数 `alloc_swap_scan_cluster`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   942  		swap_cluster_assert_empty(ci, ci_off, 1, false);
   943  		/* Fake shadow placeholder with no flag, hibernation does not use the zeromap */
   944  		__swap_table_set(ci, ci_off, __swp_tb_mk_count(shadow_to_swp_tb(NULL, 0), 1));
   945  	} else {
   946  		/* Allocation without folio is only possible with hibernation */
   947  		WARN_ON_ONCE(1);
   948  		return false;
   949  	}
   950  
   951  	/*
   952  	 * The first allocation in a cluster makes the
   953  	 * cluster exclusive to this order
   954  	 */
   955  	if (cluster_is_empty(ci))
   956  		ci->order = order;
   957  	ci->count += nr_pages;
   958  	swap_range_alloc(si, nr_pages);
   959  
   960  	return true;
   961  }
   962  
   963  /* Try use a new cluster for current CPU and allocate from it. */
   964  static unsigned int alloc_swap_scan_cluster(struct swap_info_struct *si,
   965  					    struct swap_cluster_info *ci,
   966  					    struct folio *folio, unsigned long offset)
   967> {
   968  	unsigned int next = SWAP_ENTRY_INVALID, found = SWAP_ENTRY_INVALID;
   969  	unsigned long start = ALIGN_DOWN(offset, SWAPFILE_CLUSTER);
   970  	unsigned int order = likely(folio) ? folio_order(folio) : 0;
   971  	unsigned long end = start + SWAPFILE_CLUSTER;
   972  	unsigned int nr_pages = 1 << order;
   973  	bool need_reclaim, ret, usable;
   974  
   975  	lockdep_assert_held(&ci->lock);
   976  	VM_WARN_ON(!cluster_is_usable(ci, order));
   977  
   978  	if (end < nr_pages || ci->count + nr_pages > SWAPFILE_CLUSTER)
   979  		goto out;
   980  
   981  	for (end -= nr_pages; offset <= end; offset += nr_pages) {
   982  		need_reclaim = false;
   983  		if (!cluster_scan_range(si, ci, offset, nr_pages, &need_reclaim))
   984  			continue;
   985  		if (need_reclaim) {
   986  			ret = cluster_reclaim_range(si, ci, offset, order, &usable);
```

## [6] ORD（类型一致性）`mm/swapfile.c:888` 函数 `cluster_scan_range`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   863  		return false;
   864  	}
   865  	*usable = true;
   866  
   867  	/* Fast path, no need to scan if the whole cluster is empty */
   868  	if (cluster_is_empty(ci))
   869  		return true;
   870  
   871  	/*
   872  	 * Recheck the range no matter reclaim succeeded or not, the slot
   873  	 * could have been be freed while we are not holding the lock.
   874  	 */
   875  	for (offset = start; offset < end; offset++) {
   876  		swp_tb = __swap_table_get(ci, offset % SWAPFILE_CLUSTER);
   877  		if (!swp_tb_is_null(swp_tb))
   878  			return false;
   879  	}
   880  
   881  	return true;
   882  }
   883  
   884  static bool cluster_scan_range(struct swap_info_struct *si,
   885  			       struct swap_cluster_info *ci,
   886  			       unsigned long offset, unsigned int nr_pages,
   887  			       bool *need_reclaim)
   888> {
   889  	unsigned int ci_off = offset % SWAPFILE_CLUSTER;
   890  	unsigned int ci_end = ci_off + nr_pages;
   891  	unsigned long swp_tb;
   892  
   893  	do {
   894  		swp_tb = __swap_table_get(ci, ci_off);
   895  		if (swp_tb_is_null(swp_tb))
   896  			continue;
   897  		if (swp_tb_is_folio(swp_tb) && !__swp_tb_get_count(swp_tb)) {
   898  			if (!vm_swap_full())
   899  				return false;
   900  			*need_reclaim = true;
   901  			continue;
   902  		}
   903  		/* Slot with zero count can only be NULL or folio */
   904  		VM_WARN_ON(!swp_tb_get_count(swp_tb));
   905  		return false;
   906  	} while (++ci_off < ci_end);
   907  
```

## [7] ORD（类型一致性）`mm/swapfile.c:761` 函数 `relocate_cluster`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   736  	__free_cluster(si, ci);
   737  }
   738  
   739  /*
   740   * Must be called after freeing if ci->count != 0, moves the cluster to
   741   * nonfull list.
   742   */
   743  static void partial_free_cluster(struct swap_info_struct *si,
   744  				 struct swap_cluster_info *ci)
   745  {
   746  	VM_BUG_ON(!ci->count || ci->count == SWAPFILE_CLUSTER);
   747  	lockdep_assert_held(&ci->lock);
   748  
   749  	if (ci->flags != CLUSTER_FLAG_NONFULL)
   750  		move_cluster(si, ci, &si->nonfull_clusters[ci->order],
   751  			     CLUSTER_FLAG_NONFULL);
   752  }
   753  
   754  /*
   755   * Must be called after allocation, moves the cluster to full or frag list.
   756   * Note: allocation doesn't acquire si lock, and may drop the ci lock for
   757   * reclaim, so the cluster could be any where when called.
   758   */
   759  static void relocate_cluster(struct swap_info_struct *si,
   760  			     struct swap_cluster_info *ci)
   761> {
   762  	lockdep_assert_held(&ci->lock);
   763  
   764  	/* Discard cluster must remain off-list or on discard list */
   765  	if (cluster_is_discard(ci))
   766  		return;
   767  
   768  	if (!ci->count) {
   769  		if (ci->flags != CLUSTER_FLAG_FREE)
   770  			free_cluster(si, ci);
   771  	} else if (ci->count != SWAPFILE_CLUSTER) {
   772  		if (ci->flags != CLUSTER_FLAG_FRAG)
   773  			move_cluster(si, ci, &si->frag_clusters[ci->order],
   774  				     CLUSTER_FLAG_FRAG);
   775  	} else {
   776  		if (ci->flags != CLUSTER_FLAG_FULL)
   777  			move_cluster(si, ci, &si->full_clusters,
   778  				     CLUSTER_FLAG_FULL);
   779  	}
   780  }
```

## [8] ORD（类型一致性）`mm/swapfile.c:841` 函数 `cluster_reclaim_range`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   816  		return -ENOMEM;
   817  	spin_lock(&ci->lock);
   818  	/* Check for duplicated bad swap slots. */
   819  	if (__swap_table_xchg(ci, ci_off, SWP_TB_BAD) != SWP_TB_NULL) {
   820  		pr_warn("Duplicated bad slot offset %d\n", offset);
   821  		ret = -EINVAL;
   822  	} else {
   823  		ci->count++;
   824  	}
   825  	spin_unlock(&ci->lock);
   826  
   827  	WARN_ON(ci->count > SWAPFILE_CLUSTER);
   828  	WARN_ON(ci->flags);
   829  
   830  	return ret;
   831  }
   832  
   833  /*
   834   * Reclaim drops the ci lock, so the cluster may become unusable (freed or
   835   * stolen by a lower order). @usable will be set to false if that happens.
   836   */
   837  static bool cluster_reclaim_range(struct swap_info_struct *si,
   838  				  struct swap_cluster_info *ci,
   839  				  unsigned long start, unsigned int order,
   840  				  bool *usable)
   841> {
   842  	unsigned int nr_pages = 1 << order;
   843  	unsigned long offset = start, end = start + nr_pages;
   844  	unsigned long swp_tb;
   845  
   846  	spin_unlock(&ci->lock);
   847  	do {
   848  		swp_tb = swap_table_get(ci, offset % SWAPFILE_CLUSTER);
   849  		if (swp_tb_get_count(swp_tb))
   850  			break;
   851  		if (swp_tb_is_folio(swp_tb))
   852  			if (__try_to_reclaim_swap(si, offset, TTRS_ANYWAY) < 0)
   853  				break;
   854  	} while (++offset < end);
   855  	spin_lock(&ci->lock);
   856  
   857  	/*
   858  	 * We just dropped ci->lock so cluster could be used by another
   859  	 * order or got freed, check if it's still usable or empty.
   860  	 */
```

## [9] WT（类型一致性）`arch/x86/kernel/pvclock.c:36` 函数 `pvclock_tsc_khz`
- 原始特征：`A|return:return|pv_tsc_khz`
- 卡片：消费位置 **有**（return:return（arch/x86/kernel/pvclock.c:36））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
```c
    11  #include <linux/gfp.h>
    12  #include <linux/memblock.h>
    13  #include <linux/nmi.h>
    14  
    15  #include <asm/fixmap.h>
    16  #include <asm/pvclock.h>
    17  #include <asm/vgtod.h>
    18  
    19  static u8 valid_flags __read_mostly = 0;
    20  static struct pvclock_vsyscall_time_info *pvti_cpu0_va __read_mostly;
    21  
    22  void pvclock_set_flags(u8 flags)
    23  {
    24  	valid_flags = flags;
    25  }
    26  
    27  unsigned long pvclock_tsc_khz(struct pvclock_vcpu_time_info *src)
    28  {
    29  	u64 pv_tsc_khz = 1000000ULL << 32;
    30  
    31  	do_div(pv_tsc_khz, src->tsc_to_system_mul);
    32  	if (src->tsc_shift < 0)
    33  		pv_tsc_khz <<= -src->tsc_shift;
    34  	else
    35  		pv_tsc_khz >>= src->tsc_shift;
    36> 	return pv_tsc_khz;
    37  }
    38  
    39  void pvclock_touch_watchdogs(void)
    40  {
    41  	touch_softlockup_watchdog_sync();
    42  	clocksource_touch_watchdog();
    43  	rcu_cpu_stall_reset();
    44  	reset_hung_task_detector();
    45  }
    46  
    47  static atomic64_t last_value = ATOMIC64_INIT(0);
    48  
    49  void pvclock_resume(void)
    50  {
    51  	atomic64_set(&last_value, 0);
    52  }
    53  
    54  u8 pvclock_read_flags(struct pvclock_vcpu_time_info *src)
    55  {
```

## [10] WT（类型一致性）`arch/sparc/kernel/of_device_32.c:332` 函数 `build_device_resources`
- 原始特征：`A|assign:r->end|result+size-1`
- 卡片：消费位置 **有**（assign:r->end（arch/sparc/kernel/of_device_32.c:332））；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **没有检查**（目标 r->end 是成员，类型没查）
```c
   307  
   308  			pbus = of_match_bus(pp);
   309  			pbus->count_cells(dp, &pna, &pns);
   310  
   311  			if (build_one_resource(dp, dbus, pbus, addr,
   312  					       dna, dns, pna))
   313  				break;
   314  
   315  			flags = pbus->get_flags(addr, flags);
   316  
   317  			dna = pna;
   318  			dns = pns;
   319  			dbus = pbus;
   320  		}
   321  
   322  	build_res:
   323  		memset(r, 0, sizeof(*r));
   324  
   325  		if (of_resource_verbose)
   326  			printk("%pOF reg[%d] -> %llx\n",
   327  			       op->dev.of_node, index,
   328  			       result);
   329  
   330  		if (result != OF_BAD_ADDR) {
   331  			r->start = result & 0xffffffff;
   332> 			r->end = result + size - 1;
   333  			r->flags = flags | ((result >> 32ULL) & 0xffUL);
   334  		}
   335  		r->name = op->dev.of_node->full_name;
   336  	}
   337  }
   338  
   339  static struct platform_device * __init scan_one_device(struct device_node *dp,
   340  						 struct device *parent)
   341  {
   342  	struct platform_device *op = kzalloc_obj(*op);
   343  	const struct linux_prom_irqs *intr;
   344  	struct dev_archdata *sd;
   345  	int len, i;
   346  
   347  	if (!op)
   348  		return NULL;
   349  
   350  	sd = &op->dev.archdata;
   351  	sd->op = op;
```

## [11] WK（实现一致性）`arch/powerpc/mm/book3s64/slice.c:817` 函数 `vma_mmu_pagesize`
- 原始特征：`WK|vma_mmu_pagesize|powerpc|vma_kernel_pagesize|conditional-effect|radix_enabled()`
- 卡片：消费位置 **有**（原始特征给出了调用处或调用方依赖）；编入 -；架构依据 **有**（受影响架构：powerpc）；反证 **没有检查**（）
```c
   792  {
   793  	const struct slice_mask *maskp;
   794  	unsigned int psize = mm_ctx_user_psize(&mm->context);
   795  
   796  	VM_BUG_ON(radix_enabled());
   797  
   798  	maskp = slice_mask_for_size(&mm->context, psize);
   799  
   800  	/* We need to account for 4k slices too */
   801  	if (IS_ENABLED(CONFIG_PPC_64K_PAGES) && psize == MMU_PAGE_64K) {
   802  		const struct slice_mask *compat_maskp;
   803  		struct slice_mask available;
   804  
   805  		compat_maskp = slice_mask_for_size(&mm->context, MMU_PAGE_4K);
   806  		slice_or_mask(&available, maskp, compat_maskp);
   807  		return !slice_check_range_fits(mm, &available, addr, len);
   808  	}
   809  
   810  	return !slice_check_range_fits(mm, maskp, addr, len);
   811  }
   812  
   813  unsigned long vma_mmu_pagesize(struct vm_area_struct *vma)
   814  {
   815  	/* With radix we don't use slice, so derive it from vma*/
   816  	if (radix_enabled())
   817> 		return vma_kernel_pagesize(vma);
   818  
   819  	return 1UL << mmu_psize_to_shift(get_slice_psize(vma->vm_mm, vma->vm_start));
   820  }
   821  #endif
   822  
```

## [12] WK（实现一致性）`arch/arm/mm/init.c:419` 函数 `free_initmem`
- 原始特征：`WK|free_initmem|arm|free_initmem_default|conditional-effect|!machine_is_integrator()&&!machine_is_cintegrator()`
- 卡片：消费位置 **有**（原始特征给出了调用处或调用方依赖）；编入 -；架构依据 **有**（受影响架构：arm）；反证 **没有检查**（）
```c
   394  	stop_machine(__fix_kernmem_perms, NULL, NULL);
   395  }
   396  
   397  static int __mark_rodata_ro(void *unused)
   398  {
   399  	update_sections_early(ro_perms, ARRAY_SIZE(ro_perms));
   400  	return 0;
   401  }
   402  
   403  void mark_rodata_ro(void)
   404  {
   405  	stop_machine(__mark_rodata_ro, NULL, NULL);
   406  	arm_debug_checkwx();
   407  }
   408  
   409  #else
   410  static inline void fix_kernmem_perms(void) { }
   411  #endif /* CONFIG_STRICT_KERNEL_RWX */
   412  
   413  void free_initmem(void)
   414  {
   415  	fix_kernmem_perms();
   416  
   417  	poison_init_mem(__init_begin, __init_end - __init_begin);
   418  	if (!machine_is_integrator() && !machine_is_cintegrator())
   419> 		free_initmem_default(-1);
   420  }
   421  
   422  #ifdef CONFIG_BLK_DEV_INITRD
   423  void free_initrd_mem(unsigned long start, unsigned long end)
   424  {
   425  	if (start == initrd_start)
   426  		start = round_down(start, PAGE_SIZE);
   427  	if (end == initrd_end)
   428  		end = round_up(end, PAGE_SIZE);
   429  
   430  	poison_init_mem((void *)start, PAGE_ALIGN(end) - start);
   431  	free_reserved_area((void *)start, (void *)end, -1, "initrd");
   432  }
   433  #endif
   434  
   435  #ifdef CONFIG_EXECMEM
   436  
   437  #ifdef CONFIG_XIP_KERNEL
   438  /*
```

## [13] WT（类型一致性）`arch/x86/kernel/tsc.c:645` 函数 `quick_pit_calibrate`
- 原始特征：`A|return:return|delta`
- 卡片：消费位置 **有**（return:return（arch/x86/kernel/tsc.c:645））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
```c
   620  			if (!pit_verify_msb(0xfe - i))
   621  				break;
   622  			goto success;
   623  		}
   624  	}
   625  	pr_info("Fast TSC calibration failed\n");
   626  	return 0;
   627  
   628  success:
   629  	/*
   630  	 * Ok, if we get here, then we've seen the
   631  	 * MSB of the PIT decrement 'i' times, and the
   632  	 * error has shrunk to less than 500 ppm.
   633  	 *
   634  	 * As a result, we can depend on there not being
   635  	 * any odd delays anywhere, and the TSC reads are
   636  	 * reliable (within the error).
   637  	 *
   638  	 * kHz = ticks / time-in-seconds / 1000;
   639  	 * kHz = (t2 - t1) / (I * 256 / PIT_TICK_RATE) / 1000
   640  	 * kHz = ((t2 - t1) * PIT_TICK_RATE) / (I * 256 * 1000)
   641  	 */
   642  	delta *= PIT_TICK_RATE;
   643  	do_div(delta, i*256*1000);
   644  	pr_info("Fast TSC calibration using PIT\n");
   645> 	return delta;
   646  }
   647  
   648  /**
   649   * native_calibrate_tsc - determine TSC frequency
   650   * Determine TSC frequency via CPUID, else return 0.
   651   */
   652  unsigned long native_calibrate_tsc(void)
   653  {
   654  	unsigned int eax_denominator, ebx_numerator, ecx_hz, edx;
   655  	unsigned int crystal_khz;
   656  
   657  	if (boot_cpu_data.x86_vendor != X86_VENDOR_INTEL)
   658  		return 0;
   659  
   660  	if (boot_cpu_data.cpuid_level < CPUID_LEAF_TSC)
   661  		return 0;
   662  
   663  	eax_denominator = ebx_numerator = ecx_hz = edx = 0;
   664  
```

## [14] WK（实现一致性）`arch/x86/kernel/uprobes.c:1146` 函数 `set_swbp`
- 原始特征：`WK|set_swbp|x86|uprobe_write_opcode|early-return|should_optimize(auprobe)&&ret`
- 卡片：消费位置 **有**（原始特征给出了调用处或调用方依赖）；编入 x；架构依据 **有**（受影响架构：x86）；反证 **没有检查**（）
```c
  1121  
  1122  	err = copy_from_vaddr(mm, vaddr, &insn, OPT_INSN_SIZE);
  1123  	if (err)
  1124  		return err;
  1125  	return __is_optimized(mm, (uprobe_opcode_t *)&insn, vaddr);
  1126  }
  1127  
  1128  static bool should_optimize(struct arch_uprobe *auprobe)
  1129  {
  1130  	return !test_bit(ARCH_UPROBE_FLAG_OPTIMIZE_FAIL, &auprobe->flags) &&
  1131  		test_bit(ARCH_UPROBE_FLAG_CAN_OPTIMIZE, &auprobe->flags);
  1132  }
  1133  
  1134  int set_swbp(struct arch_uprobe *auprobe, struct vm_area_struct *vma,
  1135  	     unsigned long vaddr)
  1136  {
  1137  	if (should_optimize(auprobe)) {
  1138  		/*
  1139  		 * We could race with another thread that already optimized the probe,
  1140  		 * so let's not overwrite it with int3 again in this case.
  1141  		 */
  1142  		int ret = is_optimized(vma->vm_mm, vaddr);
  1143  		if (ret < 0)
  1144  			return ret;
  1145  		if (ret)
  1146> 			return 0;
  1147  	}
  1148  	return uprobe_write_opcode(auprobe, vma, vaddr, UPROBE_SWBP_INSN,
  1149  				   true /* is_register */);
  1150  }
  1151  
  1152  int set_orig_insn(struct arch_uprobe *auprobe, struct vm_area_struct *vma,
  1153  		  unsigned long vaddr)
  1154  {
  1155  	if (test_bit(ARCH_UPROBE_FLAG_CAN_OPTIMIZE, &auprobe->flags)) {
  1156  		int ret = is_optimized(vma->vm_mm, vaddr);
  1157  		if (ret < 0)
  1158  			return ret;
  1159  		if (ret) {
  1160  			ret = swbp_unoptimize(auprobe, vma, vaddr);
  1161  			WARN_ON_ONCE(ret);
  1162  			return ret;
  1163  		}
  1164  	}
  1165  	return uprobe_write_opcode(auprobe, vma, vaddr, *(uprobe_opcode_t *)&auprobe->insn,
```

## [15] WT（类型一致性）`arch/xtensa/mm/cache.c:143` 函数 `flush_dcache_folio`
- 原始特征：`A|assign:temp|folio_pos(folio)`
- 卡片：消费位置 **有**（assign:temp（arch/xtensa/mm/cache.c:143））；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
```c
   118  EXPORT_SYMBOL(copy_user_highpage);
   119  
   120  /*
   121   * Any time the kernel writes to a user page cache page, or it is about to
   122   * read from a page cache page this routine is called.
   123   *
   124   */
   125  
   126  void flush_dcache_folio(struct folio *folio)
   127  {
   128  	struct address_space *mapping = folio_flush_mapping(folio);
   129  
   130  	/*
   131  	 * If we have a mapping but the page is not mapped to user-space
   132  	 * yet, we simply mark this page dirty and defer flushing the 
   133  	 * caches until update_mmu().
   134  	 */
   135  
   136  	if (mapping && !mapping_mapped(mapping)) {
   137  		if (!test_bit(PG_arch_1, &folio->flags.f))
   138  			set_bit(PG_arch_1, &folio->flags.f);
   139  		return;
   140  
   141  	} else {
   142  		unsigned long phys = folio_pfn(folio) * PAGE_SIZE;
   143> 		unsigned long temp = folio_pos(folio);
   144  		unsigned int i, nr = folio_nr_pages(folio);
   145  		unsigned long alias = !(DCACHE_ALIAS_EQ(temp, phys));
   146  		unsigned long virt;
   147  
   148  		/* 
   149  		 * Flush the page in kernel space and user space.
   150  		 * Note that we can omit that step if aliasing is not
   151  		 * an issue, but we do have to synchronize I$ and D$
   152  		 * if we have a mapping.
   153  		 */
   154  
   155  		if (!alias && !mapping)
   156  			return;
   157  
   158  		preempt_disable();
   159  		for (i = 0; i < nr; i++) {
   160  			virt = TLBTEMP_BASE_1 + (phys & DCACHE_ALIAS_MASK);
   161  			__flush_invalidate_dcache_page_alias(virt, phys);
   162  
```

## [16] ORD（类型一致性）`mm/swap_table.h:326` 函数 `__swap_cgroup_get`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 -；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   301  
   302  	VM_WARN_ON(!swp_tb_is_countable(swp_tb));
   303  	swp_tb &= ~SWP_TB_ZERO_FLAG;
   304  	__swap_table_set(ci, ci_off, swp_tb);
   305  #else
   306  	lockdep_assert_held(&ci->lock);
   307  	__clear_bit(ci_off, ci->zero_bitmap);
   308  #endif
   309  }
   310  
   311  #ifdef CONFIG_MEMCG
   312  static inline void __swap_cgroup_set(struct swap_cluster_info *ci,
   313  		unsigned int ci_off, unsigned long nr, unsigned short id)
   314  {
   315  	lockdep_assert_held(&ci->lock);
   316  	VM_WARN_ON_ONCE(ci_off >= SWAPFILE_CLUSTER);
   317  	if (WARN_ON_ONCE(!ci->memcg_table))
   318  		return;
   319  	do {
   320  		ci->memcg_table->id[ci_off++] = id;
   321  	} while (--nr);
   322  }
   323  
   324  static inline unsigned short __swap_cgroup_get(struct swap_cluster_info *ci,
   325  					       unsigned int ci_off)
   326> {
   327  	lockdep_assert_held(&ci->lock);
   328  	VM_WARN_ON_ONCE(ci_off >= SWAPFILE_CLUSTER);
   329  	if (unlikely(!ci->memcg_table))
   330  		return 0;
   331  	return ci->memcg_table->id[ci_off];
   332  }
   333  
   334  static inline unsigned short __swap_cgroup_clear(struct swap_cluster_info *ci,
   335  						 unsigned int ci_off,
   336  						 unsigned long nr)
   337  {
   338  	unsigned short old = __swap_cgroup_get(ci, ci_off);
   339  
   340  	if (!old)
   341  		return 0;
   342  	do {
   343  		VM_WARN_ON_ONCE(ci->memcg_table->id[ci_off] != old);
   344  		ci->memcg_table->id[ci_off++] = 0;
   345  	} while (--nr);
```

## [17] WT（类型一致性）`arch/x86/kernel/amd_nb.c:166` 函数 `amd_get_mmconfig_range`
- 原始特征：`A|assign:res->start|base ; A|assign:res->end|base+(1ULL<<(segn_busn_bits+20))-1`
- 卡片：消费位置 **有**（assign:res->start（arch/x86/kernel/amd_nb.c:166））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **没有检查**（目标 res->start 是成员，类型没查）
```c
   141  
   142  struct resource *amd_get_mmconfig_range(struct resource *res)
   143  {
   144  	u64 base, msr;
   145  	unsigned int segn_busn_bits;
   146  
   147  	if (boot_cpu_data.x86_vendor != X86_VENDOR_AMD &&
   148  	    boot_cpu_data.x86_vendor != X86_VENDOR_HYGON)
   149  		return NULL;
   150  
   151  	/* Assume CPUs from Fam10h have mmconfig, although not all VMs do */
   152  	if (boot_cpu_data.x86 < 0x10 ||
   153  	    rdmsrq_safe(MSR_FAM10H_MMIO_CONF_BASE, &msr))
   154  		return NULL;
   155  
   156  	/* mmconfig is not enabled */
   157  	if (!(msr & FAM10H_MMIO_CONF_ENABLE))
   158  		return NULL;
   159  
   160  	base = msr & (FAM10H_MMIO_CONF_BASE_MASK<<FAM10H_MMIO_CONF_BASE_SHIFT);
   161  
   162  	segn_busn_bits = (msr >> FAM10H_MMIO_CONF_BUSRANGE_SHIFT) &
   163  			 FAM10H_MMIO_CONF_BUSRANGE_MASK;
   164  
   165  	res->flags = IORESOURCE_MEM;
   166> 	res->start = base;
   167  	res->end = base + (1ULL<<(segn_busn_bits + 20)) - 1;
   168  	return res;
   169  }
   170  
   171  int amd_get_subcaches(int cpu)
   172  {
   173  	struct pci_dev *link = node_to_amd_nb(topology_amd_node_id(cpu))->link;
   174  	unsigned int mask;
   175  
   176  	if (!amd_nb_has_feature(AMD_NB_L3_PARTITIONING))
   177  		return 0;
   178  
   179  	pci_read_config_dword(link, 0x1d4, &mask);
   180  
   181  	return (mask >> (4 * cpu_data(cpu).topo.core_id)) & 0xf;
   182  }
   183  
   184  int amd_set_subcaches(int cpu, unsigned long mask)
   185  {
```

## [18] ORD（类型一致性）`mm/swapfile.c:501` 函数 `swap_cluster_assert_empty`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   476  			swap_cluster_free_table(ci);
   477  			return -ENOMEM;
   478  		}
   479  	}
   480  #endif
   481  
   482  #if !SWAP_TABLE_HAS_ZEROFLAG
   483  	VM_WARN_ON_ONCE(ci->zero_bitmap);
   484  	ci->zero_bitmap = bitmap_zalloc(SWAPFILE_CLUSTER, gfp);
   485  	if (!ci->zero_bitmap) {
   486  		swap_cluster_free_table(ci);
   487  		return -ENOMEM;
   488  	}
   489  #endif
   490  	return 0;
   491  }
   492  
   493  /*
   494   * Sanity check to ensure nothing leaked, and the specified range is empty.
   495   * One special case is that bad slots can't be freed, so check the number of
   496   * bad slots for swapoff, and non-swapoff path must never free bad slots.
   497   */
   498  static void swap_cluster_assert_empty(struct swap_cluster_info *ci,
   499  				      unsigned int ci_off, unsigned int nr,
   500  				      bool swapoff)
   501> {
   502  	unsigned int ci_end = ci_off + nr;
   503  	unsigned long swp_tb;
   504  	int bad_slots = 0;
   505  
   506  	if (!IS_ENABLED(CONFIG_DEBUG_VM) && !swapoff)
   507  		return;
   508  
   509  	do {
   510  		swp_tb = __swap_table_get(ci, ci_off);
   511  		if (swp_tb_is_bad(swp_tb))
   512  			bad_slots++;
   513  		else
   514  			WARN_ON_ONCE(!swp_tb_is_null(swp_tb));
   515  		WARN_ON_ONCE(__swap_cgroup_get(ci, ci_off));
   516  	} while (++ci_off < ci_end);
   517  
   518  	WARN_ON_ONCE(bad_slots != (swapoff ? ci->count : 0));
   519  	WARN_ON_ONCE(nr == SWAPFILE_CLUSTER && ci->extend_table);
   520  }
```

## [19] ORD（类型一致性）`mm/swap_table.h:242` 函数 `__swap_table_get`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 -；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   217   * the swap cluster must be locked.
   218   */
   219  static inline void __swap_table_set(struct swap_cluster_info *ci,
   220  				    unsigned int off, unsigned long swp_tb)
   221  {
   222  	atomic_long_t *table = rcu_dereference_protected(ci->table, true);
   223  
   224  	lockdep_assert_held(&ci->lock);
   225  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   226  	atomic_long_set(&table[off], swp_tb);
   227  }
   228  
   229  static inline unsigned long __swap_table_xchg(struct swap_cluster_info *ci,
   230  					      unsigned int off, unsigned long swp_tb)
   231  {
   232  	atomic_long_t *table = rcu_dereference_protected(ci->table, true);
   233  
   234  	lockdep_assert_held(&ci->lock);
   235  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   236  	/* Ordering is guaranteed by cluster lock, relax */
   237  	return atomic_long_xchg_relaxed(&table[off], swp_tb);
   238  }
   239  
   240  static inline unsigned long __swap_table_get(struct swap_cluster_info *ci,
   241  					     unsigned int off)
   242> {
   243  	atomic_long_t *table;
   244  
   245  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   246  	table = rcu_dereference_check(ci->table, lockdep_is_held(&ci->lock));
   247  
   248  	return atomic_long_read(&table[off]);
   249  }
   250  
   251  static inline unsigned long swap_table_get(struct swap_cluster_info *ci,
   252  					unsigned int off)
   253  {
   254  	atomic_long_t *table;
   255  	unsigned long swp_tb;
   256  
   257  	VM_WARN_ON_ONCE(off >= SWAPFILE_CLUSTER);
   258  
   259  	rcu_read_lock();
   260  	table = rcu_dereference(ci->table);
   261  	swp_tb = table ? atomic_long_read(&table[off]) : null_to_swp_tb();
```

## [20] WT（类型一致性）`arch/x86/kernel/e820.c:1132` 函数 `e820__reserve_resources`
- 原始特征：`A|assign:res->end|end`
- 卡片：消费位置 **有**（assign:res->end（arch/x86/kernel/e820.c:1132））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **没有检查**（目标 res->end 是成员，类型没查）
```c
  1107  	}
  1108  }
  1109  
  1110  /*
  1111   * Mark E820 system regions as busy for the resource manager:
  1112   */
  1113  __init void e820__reserve_resources(void)
  1114  {
  1115  	u32 idx;
  1116  	struct resource *res;
  1117  	u64 end;
  1118  
  1119  	res = memblock_alloc_or_panic(sizeof(*res) * e820_table->nr_entries,
  1120  			     SMP_CACHE_BYTES);
  1121  	e820_res = res;
  1122  
  1123  	for (idx = 0; idx < e820_table->nr_entries; idx++) {
  1124  		struct e820_entry *entry = e820_table->entries + idx;
  1125  
  1126  		end = entry->addr + entry->size - 1;
  1127  		if (end != (resource_size_t)end) {
  1128  			res++;
  1129  			continue;
  1130  		}
  1131  		res->start = entry->addr;
  1132> 		res->end   = end;
  1133  		res->name  = e820_type_to_string(entry);
  1134  		res->flags = e820_type_to_iomem_type(entry);
  1135  		res->desc  = e820_type_to_iores_desc(entry);
  1136  
  1137  		/*
  1138  		 * Skip and don't register device regions that could be conflicted
  1139  		 * with PCI device BAR resources. They get inserted later in
  1140  		 * pcibios_resource_survey() -> e820__reserve_resources_late():
  1141  		 */
  1142  		if (!e820_device_region(entry->type, res)) {
  1143  			res->flags |= IORESOURCE_BUSY;
  1144  			insert_resource(&iomem_resource, res);
  1145  		}
  1146  		res++;
  1147  	}
  1148  
  1149  	/* Expose the kexec e820 table to sysfs: */
  1150  	for (idx = 0; idx < e820_table_kexec->nr_entries; idx++) {
  1151  		struct e820_entry *entry = e820_table_kexec->entries + idx;
```

## [21] ORD（类型一致性）`mm/swapfile.c:178` 函数 `swap_only_has_cache`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   153   * off-list bit in the atomic counter, updates no longer need any lock
   154   * to check the list status.
   155   *
   156   * This bit will be set if the device is not on the plist and not
   157   * usable, will be cleared if the device is on the plist.
   158   */
   159  #define SWAP_USAGE_OFFLIST_BIT (1UL << (BITS_PER_TYPE(atomic_t) - 2))
   160  #define SWAP_USAGE_COUNTER_MASK (~SWAP_USAGE_OFFLIST_BIT)
   161  static long swap_usage_in_pages(struct swap_info_struct *si)
   162  {
   163  	return atomic_long_read(&si->inuse_pages) & SWAP_USAGE_COUNTER_MASK;
   164  }
   165  
   166  /* Reclaim the swap entry anyway if possible */
   167  #define TTRS_ANYWAY		0x1
   168  /*
   169   * Reclaim the swap entry if there are no more mappings of the
   170   * corresponding page
   171   */
   172  #define TTRS_UNMAPPED		0x2
   173  /* Reclaim the swap entry if swap is getting full */
   174  #define TTRS_FULL		0x4
   175  
   176  static bool swap_only_has_cache(struct swap_cluster_info *ci,
   177  				unsigned long offset, int nr_pages)
   178> {
   179  	unsigned int ci_off = offset % SWAPFILE_CLUSTER;
   180  	unsigned int ci_end = ci_off + nr_pages;
   181  	unsigned long swp_tb;
   182  
   183  	do {
   184  		swp_tb = __swap_table_get(ci, ci_off);
   185  		VM_WARN_ON_ONCE(!swp_tb_is_folio(swp_tb));
   186  		if (swp_tb_get_count(swp_tb))
   187  			return false;
   188  	} while (++ci_off < ci_end);
   189  
   190  	return true;
   191  }
   192  
   193  /*
   194   * returns number of pages in the folio that backs the swap entry. If positive,
   195   * the folio was reclaimed. If negative, the folio was not reclaimed. If 0, no
   196   * folio was associated with the swap entry.
   197   */
```

## [22] ORD（类型一致性）`mm/swapfile.c:745` 函数 `partial_free_cluster`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   720  {
   721  	VM_BUG_ON(ci->count != 0);
   722  	VM_BUG_ON(ci->flags == CLUSTER_FLAG_FREE);
   723  	lockdep_assert_held(&ci->lock);
   724  
   725  	/*
   726  	 * If the swap is discardable, prepare discard the cluster
   727  	 * instead of free it immediately. The cluster will be freed
   728  	 * after discard.
   729  	 */
   730  	if ((si->flags & (SWP_WRITEOK | SWP_PAGE_DISCARD)) ==
   731  	    (SWP_WRITEOK | SWP_PAGE_DISCARD)) {
   732  		swap_cluster_schedule_discard(si, ci);
   733  		return;
   734  	}
   735  
   736  	__free_cluster(si, ci);
   737  }
   738  
   739  /*
   740   * Must be called after freeing if ci->count != 0, moves the cluster to
   741   * nonfull list.
   742   */
   743  static void partial_free_cluster(struct swap_info_struct *si,
   744  				 struct swap_cluster_info *ci)
   745> {
   746  	VM_BUG_ON(!ci->count || ci->count == SWAPFILE_CLUSTER);
   747  	lockdep_assert_held(&ci->lock);
   748  
   749  	if (ci->flags != CLUSTER_FLAG_NONFULL)
   750  		move_cluster(si, ci, &si->nonfull_clusters[ci->order],
   751  			     CLUSTER_FLAG_NONFULL);
   752  }
   753  
   754  /*
   755   * Must be called after allocation, moves the cluster to full or frag list.
   756   * Note: allocation doesn't acquire si lock, and may drop the ci lock for
   757   * reclaim, so the cluster could be any where when called.
   758   */
   759  static void relocate_cluster(struct swap_info_struct *si,
   760  			     struct swap_cluster_info *ci)
   761  {
   762  	lockdep_assert_held(&ci->lock);
   763  
   764  	/* Discard cluster must remain off-list or on discard list */
```

## [23] ORD（类型一致性）`mm/swapfile.c:409` 函数 `cluster_offset`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
```c
   384  
   385  static inline bool cluster_table_is_alloced(struct swap_cluster_info *ci)
   386  {
   387  	return rcu_dereference_protected(ci->table, lockdep_is_held(&ci->lock));
   388  }
   389  
   390  static inline bool cluster_is_usable(struct swap_cluster_info *ci, int order)
   391  {
   392  	if (unlikely(ci->flags > CLUSTER_FLAG_USABLE))
   393  		return false;
   394  	if (!cluster_table_is_alloced(ci))
   395  		return false;
   396  	if (!order)
   397  		return true;
   398  	return cluster_is_empty(ci) || order == ci->order;
   399  }
   400  
   401  static inline unsigned int cluster_index(struct swap_info_struct *si,
   402  					 struct swap_cluster_info *ci)
   403  {
   404  	return ci - si->cluster_info;
   405  }
   406  
   407  static inline unsigned int cluster_offset(struct swap_info_struct *si,
   408  					  struct swap_cluster_info *ci)
   409> {
   410  	return cluster_index(si, ci) * SWAPFILE_CLUSTER;
   411  }
   412  
   413  static void swap_cluster_free_table_folio_rcu_cb(struct rcu_head *head)
   414  {
   415  	struct folio *folio;
   416  
   417  	folio = page_folio(container_of(head, struct page, rcu_head));
   418  	folio_put(folio);
   419  }
   420  
   421  static void swap_cluster_free_table(struct swap_cluster_info *ci)
   422  {
   423  	struct swap_table *table;
   424  
   425  #ifdef CONFIG_MEMCG
   426  	kfree(ci->memcg_table);
   427  	ci->memcg_table = NULL;
   428  #endif
```

## [24] WT（类型一致性）`arch/riscv/mm/ptdump.c:293` 函数 `note_page`
- 原始特征：`A|assign:st->start_pa|pa ; A|assign:st->last_pa|pa ; A|assign:st->start_pa|pa ; A|assign:st->last_pa|pa ; A|assign:st->last_pa|pa`
- 卡片：消费位置 **有**（assign:st->start_pa（arch/riscv/mm/ptdump.c:293））；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **没有检查**（目标 st->start_pa 是成员，类型没查）
```c
   268  
   269  	if ((st->current_prot & (_PAGE_WRITE | _PAGE_EXEC)) !=
   270  	    (_PAGE_WRITE | _PAGE_EXEC))
   271  		return;
   272  
   273  	WARN_ONCE(1, "riscv/mm: Found insecure W+X mapping at address %p/%pS\n",
   274  		  (void *)st->start_address, (void *)st->start_address);
   275  
   276  	st->wx_pages += (addr - st->start_address) / PAGE_SIZE;
   277  }
   278  
   279  static void note_page(struct ptdump_state *pt_st, unsigned long addr,
   280  		      int level, u64 val)
   281  {
   282  	struct pg_state *st = container_of(pt_st, struct pg_state, ptdump);
   283  	u64 pa = PFN_PHYS(pte_pfn(__pte(val)));
   284  	u64 prot = 0;
   285  
   286  	if (level >= 0)
   287  		prot = val & pg_level[level].mask;
   288  
   289  	if (st->level == -1) {
   290  		st->level = level;
   291  		st->current_prot = prot;
   292  		st->start_address = addr;
   293> 		st->start_pa = pa;
   294  		st->last_pa = pa;
   295  		pt_dump_seq_printf(st->seq, "---[ %s ]---\n", st->marker->name);
   296  	} else if (prot != st->current_prot ||
   297  		   level != st->level || addr >= st->marker[1].start_address) {
   298  		if (st->current_prot) {
   299  			note_prot_wx(st, addr);
   300  			dump_addr(st, addr);
   301  			dump_prot(st);
   302  			pt_dump_seq_puts(st->seq, "\n");
   303  		}
   304  
   305  		while (addr >= st->marker[1].start_address) {
   306  			st->marker++;
   307  			pt_dump_seq_printf(st->seq, "---[ %s ]---\n",
   308  					   st->marker->name);
   309  		}
   310  
   311  		st->start_address = addr;
   312  		st->start_pa = pa;
```
