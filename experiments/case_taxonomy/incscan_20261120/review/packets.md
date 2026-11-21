# incscan 审查材料（新版本 aebb72744764|2026-11-15|Linux 7.4-rc3；两榜前 12 条合并，打乱、隐去来源和名次）

判断：完整线索（公共代码的依赖、架构条件改变保证的依据、同一对象到消费者的证据，且已排除最直接的合法解释）/ 未决 / 排除 / 未知。
排除请写原因类别。行号前的 `>` 标出报告行。源码是新版本 `aebb72744764`。

## [1] WT（类型一致性）`mm/damon/core.c:2976` 函数 `damos_set_psi_current_val`
- 原始特征：`A|assign:val|now_psi_total-last_psi_total`
- 卡片：消费位置 **有**（assign:val（mm/damon/core.c:2976））；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
  2951  static u64 damos_get_some_mem_psi_total(void)
  2952  {
  2953  	if (static_branch_likely(&psi_disabled))
  2954  		return 0;
  2955  	return div_u64(psi_system.total[PSI_AVGS][PSI_MEM * 2],
  2956  			NSEC_PER_USEC);
  2957  }
  2958  
  2959  #else	/* CONFIG_PSI */
  2960  
  2961  static inline u64 damos_get_some_mem_psi_total(void)
  2962  {
  2963  	return 0;
  2964  }
  2965  
  2966  #endif	/* CONFIG_PSI */
  2967  
  2968  static void damos_set_psi_current_val(u64 now_psi_total,
  2969  		struct damos_quota_goal *goal, struct damos *s)
  2970  {
  2971  	u64 last_psi_total = goal->last_psi_total;
  2972  	unsigned long val;
  2973  
  2974  	goal->last_psi_total = now_psi_total;
  2975  	if (last_psi_total != U64_MAX) {
  2976> 		val = now_psi_total - last_psi_total;
  2977  		if (goal->complement) {
  2978  			if (val < s->quota.reset_interval * 1000)
  2979  				val = s->quota.reset_interval * 1000 - val;
  2980  			else
  2981  				val = 0;
  2982  		}
  2983  		goal->current_value = val;
  2984  		return;
  2985  	}
  2986  	/* uninitialized last_psi_total; make no effect this round */
  2987  	if (s->quota.goal_tuner == DAMOS_QUOTA_GOAL_TUNER_CONSIST) {
  2988  		goal->current_value = goal->target_value;
  2989  		return;
  2990  	}
  2991  	/* let temporal tuner show the same achievement as in the last round */
  2992  	if (!s->quota.esz)
  2993  		goal->current_value = goal->target_value;
  2994  	else
  2995  		goal->current_value = 0;
```

## [2] WT（类型一致性）`fs/f2fs/node.c:88` 函数 `f2fs_available_free_memory`
- 原始特征：`A|assign:mem_size|get_nr_caches(sbi,F2FS_DIRTY_DENTS)`
- 卡片：消费位置 **有**（assign:mem_size（fs/f2fs/node.c:88））；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：有；函数体改过
```c
    63  	si_meminfo(&val);
    64  
    65  	/* only uses low memory */
    66  	avail_ram = val.totalram - val.totalhigh;
    67  
    68  	/*
    69  	 * give 25%, 25%, 50%, 50%, 25%, 25% memory for each components respectively
    70  	 */
    71  	if (type == FREE_NIDS) {
    72  		mem_size = (nm_i->nid_cnt[FREE_NID] *
    73  				sizeof(struct free_nid)) >> PAGE_SHIFT;
    74  		res = mem_size < ((avail_ram * nm_i->ram_thresh / 100) >> 2);
    75  	} else if (type == NAT_ENTRIES) {
    76  		/*
    77  		 * nat_cnt[] is heuristic accounting. Sample it locklessly here
    78  		 * to avoid taking nat_tree_lock in the balance path.
    79  		 */
    80  		mem_size = (data_race(READ_ONCE(nm_i->nat_cnt[TOTAL_NAT])) *
    81  				sizeof(struct nat_entry)) >> PAGE_SHIFT;
    82  		res = mem_size < ((avail_ram * nm_i->ram_thresh / 100) >> 2);
    83  		if (excess_cached_nats(sbi))
    84  			res = false;
    85  	} else if (type == DIRTY_DENTS) {
    86  		if (bdi_wb_dirty_exceeded(sbi->sb->s_bdi))
    87  			return false;
    88> 		mem_size = get_nr_caches(sbi, F2FS_DIRTY_DENTS);
    89  		res = mem_size < ((avail_ram * nm_i->ram_thresh / 100) >> 1);
    90  	} else if (type == INO_ENTRIES) {
    91  		int i;
    92  
    93  		for (i = 0; i < MAX_INO_ENTRY; i++)
    94  			mem_size += sbi->im[i].ino_num *
    95  						sizeof(struct ino_entry);
    96  		mem_size >>= PAGE_SHIFT;
    97  		res = mem_size < ((avail_ram * nm_i->ram_thresh / 100) >> 1);
    98  	} else if (type == READ_EXTENT_CACHE || type == AGE_EXTENT_CACHE) {
    99  		enum extent_type etype = type == READ_EXTENT_CACHE ?
   100  						EX_READ : EX_BLOCK_AGE;
   101  		struct extent_tree_info *eti = &sbi->extent_tree[etype];
   102  
   103  		mem_size = (atomic_read(&eti->total_ext_tree) *
   104  				sizeof(struct extent_tree) +
   105  				atomic_read(&eti->total_ext_node) *
   106  				sizeof(struct extent_node)) >> PAGE_SHIFT;
   107  		res = mem_size < ((avail_ram * nm_i->ram_thresh / 100) >> 2);
```

## [3] ORD（类型一致性）`mm/huge_memory.c:4184` 函数 `__folio_freeze_split_file`
- 原始特征：`HPAGE_PMD_ORDER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 a；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
  4159  	folio_ref_unfreeze(folio, folio_swapcache_ref_count(folio) + 1);
  4160  
  4161  	if (do_lru)
  4162  		lruvec_unlock(lruvec);
  4163  	if (ci)
  4164  		swap_cluster_unlock(ci);
  4165  out_no_split:
  4166  	local_irq_enable();
  4167  	if (anon_vma) {
  4168  		if (!ret && !folio_is_device_private(folio))
  4169  			ttu_flags = TTU_USE_SHARED_ZEROPAGE;
  4170  		remap_anon_folio(folio, 1 << old_order, ttu_flags);
  4171  	}
  4172  out_unlock:
  4173  	if (anon_vma) {
  4174  		anon_vma_unlock_write(anon_vma);
  4175  		put_anon_vma(anon_vma);
  4176  	}
  4177  
  4178  	return ret;
  4179  }
  4180  
  4181  static int __folio_freeze_split_file(struct folio *folio,
  4182  		unsigned int new_order, struct page *split_at,
  4183  		struct list_head *list, enum split_type split_type)
  4184> {
  4185  	const long old_nr_pages = folio_nr_pages(folio);
  4186  	struct address_space *mapping = folio->mapping;
  4187  	XA_STATE(xas, &mapping->i_pages, folio->index);
  4188  	struct folio *end_folio = folio_next(folio);
  4189  	struct mem_cgroup *memcg, *old_memcg;
  4190  	struct folio *new_folio, *next;
  4191  	int nr_shmem_dropped = 0;
  4192  	unsigned int min_order;
  4193  	struct lruvec *lruvec;
  4194  	pgoff_t end;
  4195  	gfp_t gfp;
  4196  	int ret = 0;
  4197  
  4198  	min_order = mapping_min_folio_order(mapping);
  4199  	if (new_order < min_order)
  4200  		return -EINVAL;
  4201  
  4202  	/*
  4203  	 * Switch to folio's memcg as xarray node allocation can happen and
```

## [4] XV（实现一致性）`mm/damon/ops-common.c:133` 函数 `damon_hugetlb_ptep_mkold`
- 原始特征：`dom|pte_mkold|*entry`
- 卡片：消费位置 **有**（编码后的值被写回或返回：*entry = pte_mkold(*entry);）；编入 -；架构依据 **有**（各架构页表项编码不同）；反证 **没有检查**（）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   108  
   109  	folio = damon_get_folio(pfn);
   110  	if (!folio)
   111  		return;
   112  
   113  	if (likely(pmd_present(pmdval)))
   114  		young |= pmdp_test_and_clear_young(vma, addr, pmd);
   115  	young |= mmu_notifier_clear_young(vma->vm_mm, addr, addr + HPAGE_PMD_SIZE);
   116  	if (young)
   117  		folio_set_young(folio);
   118  
   119  	folio_set_idle(folio);
   120  	folio_put(folio);
   121  #endif /* CONFIG_TRANSPARENT_HUGEPAGE */
   122  }
   123  
   124  #ifdef CONFIG_HUGETLB_PAGE
   125  static bool damon_hugetlb_ptep_mkold(pte_t *pte, struct mm_struct *mm,
   126  		struct vm_area_struct *vma, unsigned long addr, pte_t *entry)
   127  {
   128  	unsigned long psize = huge_page_size(hstate_vma(vma));
   129  
   130  	if (!pte_young(*entry))
   131  		return false;
   132  	*entry = huge_ptep_get_and_clear(mm, addr, pte, psize);
   133> 	*entry = pte_mkold(*entry);
   134  	set_huge_pte_at(mm, addr, pte, *entry, psize);
   135  	return true;
   136  }
   137  
   138  void damon_hugetlb_mkold(pte_t *pte, struct mm_struct *mm,
   139  		struct vm_area_struct *vma, unsigned long addr)
   140  {
   141  	bool referenced = false;
   142  	pte_t entry = huge_ptep_get(mm, addr, pte);
   143  	struct folio *folio;
   144  
   145  	folio = damon_get_monitor_folio(pte_pfn(entry));
   146  	if (!folio)
   147  		return;
   148  
   149  	referenced = damon_hugetlb_ptep_mkold(pte, mm, vma, addr, &entry);
   150  	if (mmu_notifier_clear_young(mm, addr,
   151  				     addr + huge_page_size(hstate_vma(vma))))
   152  		referenced = true;
```

## [5] P1（实现一致性）`mm/damon/ops-common.c:145` 函数 `damon_hugetlb_mkold`
- 原始特征：`pte_pfn|*pte`
- 卡片：消费位置 **有**（访问函数结果被使用：folio = damon_get_monitor_folio(pte_pfn(entry));）；编入 -；架构依据 **有**（各架构页表项编码不同）；反证 **没有检查**（）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   120  	folio_put(folio);
   121  #endif /* CONFIG_TRANSPARENT_HUGEPAGE */
   122  }
   123  
   124  #ifdef CONFIG_HUGETLB_PAGE
   125  static bool damon_hugetlb_ptep_mkold(pte_t *pte, struct mm_struct *mm,
   126  		struct vm_area_struct *vma, unsigned long addr, pte_t *entry)
   127  {
   128  	unsigned long psize = huge_page_size(hstate_vma(vma));
   129  
   130  	if (!pte_young(*entry))
   131  		return false;
   132  	*entry = huge_ptep_get_and_clear(mm, addr, pte, psize);
   133  	*entry = pte_mkold(*entry);
   134  	set_huge_pte_at(mm, addr, pte, *entry, psize);
   135  	return true;
   136  }
   137  
   138  void damon_hugetlb_mkold(pte_t *pte, struct mm_struct *mm,
   139  		struct vm_area_struct *vma, unsigned long addr)
   140  {
   141  	bool referenced = false;
   142  	pte_t entry = huge_ptep_get(mm, addr, pte);
   143  	struct folio *folio;
   144  
   145> 	folio = damon_get_monitor_folio(pte_pfn(entry));
   146  	if (!folio)
   147  		return;
   148  
   149  	referenced = damon_hugetlb_ptep_mkold(pte, mm, vma, addr, &entry);
   150  	if (mmu_notifier_clear_young(mm, addr,
   151  				     addr + huge_page_size(hstate_vma(vma))))
   152  		referenced = true;
   153  
   154  	if (referenced)
   155  		folio_set_young(folio);
   156  
   157  	folio_set_idle(folio);
   158  	folio_put(folio);
   159  }
   160  #endif	/* CONFIG_HUGETLB_PAGE */
   161  
   162  #define DAMON_MAX_SUBSCORE	(100)
   163  #define DAMON_MAX_AGE_IN_LOG	(32)
   164  
```

## [6] P1（实现一致性）`mm/damon/vaddr.c:532` 函数 `damon_va_young_addr`
- 原始特征：`pte_young|*pte ; pmd_young|*pmd`
- 卡片：消费位置 **有**（访问函数结果被使用：young = pte_young(*pte);）；编入 -；架构依据 **有**（各架构页表项编码不同）；反证 **没有检查**（）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   507  	struct mm_struct *mm;
   508  	struct damon_region *r;
   509  	struct damon_probe *p;
   510  
   511  	damon_for_each_target(t, ctx) {
   512  		mm = damon_get_mm(t);
   513  		if (!mm)
   514  			continue;
   515  		damon_for_each_region(r, t) {
   516  			if (set_samples)
   517  				r->sampling_addr = damon_rand(ctx, r->ar.start,
   518  						r->ar.end);
   519  			damon_for_each_probe(p, ctx)
   520  				damon_va_prep_probe_region(ctx, mm, r, p);
   521  		}
   522  		mmput(mm);
   523  	}
   524  }
   525  
   526  static bool damon_va_young_addr(struct folio *folio, pte_t *pte, pmd_t *pmd,
   527  		struct mm_struct *mm, unsigned long addr)
   528  {
   529  	bool young = false;
   530  
   531  	if (pte)
   532> 		young = pte_young(*pte);
   533  	else if (pmd)
   534  		young = pmd_young(*pmd);
   535  	young = young || !folio_test_idle(folio) ||
   536  		mmu_notifier_test_young(mm, addr);
   537  	return young;
   538  }
   539  
   540  static bool damon_va_filter_match(struct damon_filter *filter,
   541  		struct folio *folio, pte_t *pte, pmd_t *pmd,
   542  		struct mm_struct *mm, unsigned long addr)
   543  {
   544  	bool matched = false;
   545  
   546  	switch (filter->type) {
   547  	case DAMON_FILTER_TYPE_PGIDLE_UNSET:
   548  		if (!folio)
   549  			matched = false;
   550  		else
   551  			matched = damon_va_young_addr(folio, pte, pmd, mm,
```

## [7] WT（类型一致性）`fs/ceph/file.c:2289` 函数 `ceph_read_iter`
- 原始特征：`A|arg:folio_zero_segment#2|end ; A|arg:copy_folio_to_iter#2|end-iocb->ki_pos`
- 卡片：消费位置 **未知**（特征 arg:folio_zero_segment#2 不是赋值或返回）；编入 -；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：有；函数体改过
```c
  2264  				return -ENOMEM;
  2265  
  2266  			mask = CEPH_STAT_CAP_INLINE_DATA;
  2267  		}
  2268  
  2269  		statret = __ceph_do_getattr(inode, folio, mask, !!folio);
  2270  		if (statret < 0) {
  2271  			if (folio)
  2272  				folio_put(folio);
  2273  			if (statret == -ENODATA) {
  2274  				BUG_ON(retry_op != READ_INLINE);
  2275  				goto again;
  2276  			}
  2277  			return statret;
  2278  		}
  2279  
  2280  		i_size = i_size_read(inode);
  2281  		if (retry_op == READ_INLINE) {
  2282  			BUG_ON(ret > 0 || read > 0);
  2283  			if (iocb->ki_pos < i_size &&
  2284  			    iocb->ki_pos < PAGE_SIZE) {
  2285  				loff_t end = min_t(loff_t, i_size,
  2286  						   iocb->ki_pos + len);
  2287  				end = min_t(loff_t, end, PAGE_SIZE);
  2288  				if (statret < end)
  2289> 					folio_zero_segment(folio, statret, end);
  2290  				ret = copy_folio_to_iter(folio,
  2291  						iocb->ki_pos & ~PAGE_MASK,
  2292  						end - iocb->ki_pos, to);
  2293  				iocb->ki_pos += ret;
  2294  				read += ret;
  2295  			}
  2296  			if (iocb->ki_pos < i_size && read < len) {
  2297  				size_t zlen = min_t(size_t, len - read,
  2298  						    i_size - iocb->ki_pos);
  2299  				ret = iov_iter_zero(zlen, to);
  2300  				iocb->ki_pos += ret;
  2301  				read += ret;
  2302  			}
  2303  			folio_put(folio);
  2304  			return read;
  2305  		}
  2306  
  2307  		/* hit EOF or hole? */
  2308  		if (retry_op == CHECK_EOF && iocb->ki_pos < i_size &&
```

## [8] ORD（类型一致性）`mm/khugepaged.c:941` 函数 `collapse_policy_khugepaged`
- 原始特征：`COLLAPSE_MAX_PTES_LIMIT`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 a；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   916  	/* If there is a count for this node already, it must be acceptable */
   917  	if (cc->node_load[nid])
   918  		return false;
   919  
   920  	for (i = 0; i < MAX_NUMNODES; i++) {
   921  		if (!cc->node_load[i])
   922  			continue;
   923  		if (node_distance(nid, i) > node_reclaim_distance)
   924  			return true;
   925  	}
   926  	return false;
   927  }
   928  
   929  #define khugepaged_defrag()					\
   930  	(transparent_hugepage_flags &				\
   931  	 (1<<TRANSPARENT_HUGEPAGE_DEFRAG_KHUGEPAGED_FLAG))
   932  
   933  /* Defrag for khugepaged will enter direct reclaim/compaction if necessary */
   934  static inline gfp_t alloc_hugepage_khugepaged_gfpmask(void)
   935  {
   936  	return khugepaged_defrag() ? GFP_TRANSHUGE : GFP_TRANSHUGE_LIGHT;
   937  }
   938  
   939  /* khugepaged collapses on its own initiative, so it obeys its own settings */
   940  static void collapse_policy_khugepaged(struct collapse_policy *p)
   941> {
   942  	p->pmd.max_ptes_none = READ_ONCE(khugepaged_max_ptes_none);
   943  	p->pmd.max_ptes_swap = READ_ONCE(khugepaged_max_ptes_swap);
   944  	p->pmd.max_ptes_shared = READ_ONCE(khugepaged_max_ptes_shared);
   945  
   946  	/*
   947  	 * A sub-PMD window takes no swapped-out and no shared PTE: reading
   948  	 * pages back or breaking CoW is not worth it for an mTHP.  Empty PTEs
   949  	 * it takes all or nothing, since anything in between would let one
   950  	 * collapse feed the next.
   951  	 */
   952  	p->sub_pmd.max_ptes_none = p->pmd.max_ptes_none;
   953  	if (p->sub_pmd.max_ptes_none &&
   954  	    p->sub_pmd.max_ptes_none != COLLAPSE_MAX_PTES_LIMIT)
   955  		pr_warn_once("mTHP collapse does not support max_ptes_none values other than 0 or %u, defaulting to 0.\n",
   956  			     COLLAPSE_MAX_PTES_LIMIT);
   957  	p->sub_pmd.max_ptes_swap = 0;
   958  	p->sub_pmd.max_ptes_shared = 0;
   959  
   960  	p->anon_skip_lazyfree = true;
```

## [9] WT（类型一致性）`fs/fs-writeback.c:1228` 函数 `cgroup_writeback_by_id`
- 原始特征：`A|assign:dirty|wb_stat_sum(wb,WB_RECLAIMABLE)`
- 卡片：消费位置 **有**（assign:dirty（fs/fs-writeback.c:1228））；编入 rax；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：有；函数体改过
```c
  1203  	if (memcg_css && !css_tryget(memcg_css))
  1204  		memcg_css = NULL;
  1205  	rcu_read_unlock();
  1206  	if (!memcg_css) {
  1207  		ret = -ENOENT;
  1208  		goto out_bdi_put;
  1209  	}
  1210  
  1211  	/*
  1212  	 * And find the associated wb.  If the wb isn't there already
  1213  	 * there's nothing to flush, don't create one.
  1214  	 */
  1215  	wb = wb_get_lookup(bdi, memcg_css);
  1216  	if (!wb) {
  1217  		ret = -ENOENT;
  1218  		goto out_css_put;
  1219  	}
  1220  
  1221  	/*
  1222  	 * The caller is attempting to write out most of the target wb's
  1223  	 * currently dirty pages.  Size the work from the wb's reclaimable pages
  1224  	 * and inflate the count by 25%, which should be large enough to flush
  1225  	 * out most dirty pages while avoiding getting livelocked by concurrent
  1226  	 * dirtiers.
  1227  	 */
  1228> 	dirty = wb_stat_sum(wb, WB_RECLAIMABLE);
  1229  	dirty = dirty * 10 / 8;
  1230  
  1231  	/* issue the writeback work */
  1232  	work = kzalloc_obj(*work, GFP_NOWAIT);
  1233  	if (work) {
  1234  		work->nr_pages = dirty;
  1235  		work->sync_mode = WB_SYNC_NONE;
  1236  		work->range_cyclic = 1;
  1237  		work->reason = reason;
  1238  		work->done = done;
  1239  		work->auto_free = 1;
  1240  		wb_queue_work(wb, work);
  1241  		ret = 0;
  1242  	} else {
  1243  		ret = -ENOMEM;
  1244  	}
  1245  
  1246  	wb_put(wb);
  1247  out_css_put:
```

## [10] ORD（类型一致性）`mm/khugepaged.c:970` 函数 `collapse_policy_madvise`
- 原始特征：`HPAGE_PMD_NR`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 a；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   945  
   946  	/*
   947  	 * A sub-PMD window takes no swapped-out and no shared PTE: reading
   948  	 * pages back or breaking CoW is not worth it for an mTHP.  Empty PTEs
   949  	 * it takes all or nothing, since anything in between would let one
   950  	 * collapse feed the next.
   951  	 */
   952  	p->sub_pmd.max_ptes_none = p->pmd.max_ptes_none;
   953  	if (p->sub_pmd.max_ptes_none &&
   954  	    p->sub_pmd.max_ptes_none != COLLAPSE_MAX_PTES_LIMIT)
   955  		pr_warn_once("mTHP collapse does not support max_ptes_none values other than 0 or %u, defaulting to 0.\n",
   956  			     COLLAPSE_MAX_PTES_LIMIT);
   957  	p->sub_pmd.max_ptes_swap = 0;
   958  	p->sub_pmd.max_ptes_shared = 0;
   959  
   960  	p->anon_skip_lazyfree = true;
   961  	p->anon_require_referenced = true;
   962  	p->file_install_pmd = false;
   963  	p->file_writeback_dirty = false;
   964  	p->gfp = alloc_hugepage_khugepaged_gfpmask();
   965  	p->tva_type = TVA_KHUGEPAGED;
   966  }
   967  
   968  /* MADV_COLLAPSE was asked for explicitly, so it is not held to those */
   969  static void collapse_policy_madvise(struct collapse_policy *p)
   970> {
   971  	p->pmd.max_ptes_none = HPAGE_PMD_NR;
   972  	p->pmd.max_ptes_swap = HPAGE_PMD_NR;
   973  	p->pmd.max_ptes_shared = HPAGE_PMD_NR;
   974  	/* Never read: MADV_COLLAPSE collapses to PMD order only */
   975  	p->sub_pmd = p->pmd;
   976  
   977  	p->anon_skip_lazyfree = false;
   978  	p->anon_require_referenced = false;
   979  	p->file_install_pmd = true;
   980  	p->file_writeback_dirty = true;
   981  	p->gfp = GFP_TRANSHUGE;
   982  	p->tva_type = TVA_FORCED_COLLAPSE;
   983  }
   984  
   985  #ifdef CONFIG_NUMA
   986  static int collapse_find_target_node(struct collapse_control *cc)
   987  {
   988  	int nid, target_node = 0, max_value = 0;
   989  
```

## [11] ORD（类型一致性）`mm/swap_state.c:537` 函数 `__swap_cache_alloc_folio`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 rax；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   512  
   513  /**
   514   * __swap_cache_alloc_folio - Allocate folio for swapped out slot in swap cache.
   515   * @targ_entry: swap entry indicating the target slot
   516   * @gfp: memory allocation flags
   517   * @orders: allocation orders, must be non zero
   518   * @vmf: fault information
   519   * @mpol: NUMA memory allocation policy to be applied
   520   * @ilx: NUMA interleave index, for use only when MPOL_INTERLEAVE
   521   *
   522   * Allocate a folio in the swap cache for one swap slot, typically before
   523   * doing IO (e.g. swap in or zswap writeback). The swap slot indicated by
   524   * @targ_entry must have a non-zero swap count (swapped out).
   525   *
   526   * The returned folio is locked and is NOT on the LRU. The caller must either
   527   * add it to the LRU with folio_add_lru() so page reclaim can find it, or free
   528   * it directly once done; a folio left off the LRU is unreclaimable and leaks.
   529   *
   530   * Context: Caller must protect the swap device with reference count or locks.
   531   * Return: Returns the folio if allocation succeeded and folio is in the swap
   532   * cache. Returns error code if failed due to race, OOM or invalid arguments.
   533   */
   534  struct folio *__swap_cache_alloc_folio(swp_entry_t targ_entry, gfp_t gfp,
   535  				       unsigned long orders, struct vm_fault *vmf,
   536  				       struct mempolicy *mpol, pgoff_t ilx)
   537> {
   538  	int order, err;
   539  	struct folio *ret;
   540  	struct swap_cluster_info *ci;
   541  
   542  	ci = __swap_entry_to_cluster(targ_entry);
   543  	order = highest_order(orders);
   544  
   545  	/* orders must be non-zero, and must not exceed cluster size. */
   546  	if (WARN_ON_ONCE(!orders || (1UL << order) > SWAPFILE_CLUSTER))
   547  		return ERR_PTR(-EINVAL);
   548  
   549  	do {
   550  		ret = __swap_cache_alloc(ci, targ_entry, gfp, order,
   551  					 vmf, mpol, ilx);
   552  		if (!IS_ERR(ret))
   553  			break;
   554  		err = PTR_ERR(ret);
   555  		if (!order || (err && err != -EBUSY && err != -ENOMEM))
   556  			break;
```

## [12] ORD（类型一致性）`mm/zswap.c:1609` 函数 `zswap_is_present`
- 原始特征：`SWAPFILE_CLUSTER`
- 卡片：消费位置 **未知**（报告行没有以阶数宏为实参的调用）；编入 -；架构依据 **有**（大页面配置（如 arm64 64K）下阶数可能超过页缓存上限）；反证 **查过未见补偿**（函数里没有 MAX_PAGECACHE_ORDER 一类检查）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
  1584  	if (!ret && zswap_pool_reached_full)
  1585  		queue_work(shrink_wq, &zswap_shrink_work);
  1586  check_old:
  1587  	/*
  1588  	 * If the zswap store fails or zswap is disabled, we must invalidate
  1589  	 * the possibly stale entries which were previously stored at the
  1590  	 * offsets corresponding to each page of the folio. Otherwise,
  1591  	 * writeback could overwrite the new data in the swapfile.
  1592  	 */
  1593  	if (!ret)
  1594  		zswap_invalidate(swp_type(swp), swp_offset(swp), nr_pages);
  1595  
  1596  	return ret;
  1597  }
  1598  
  1599  /**
  1600   * zswap_is_present() - is any slot in [entry, entry + nr) in zswap?
  1601   * @entry: base swap entry of the range
  1602   * @nr: number of contiguous slots to check
  1603   *
  1604   * Context: The caller must keep the range pinned, otherwise the answer can
  1605   * change under it.
  1606   * Return: true if at least one slot in the range is in zswap.
  1607   */
  1608  static bool zswap_is_present(swp_entry_t entry, unsigned int nr)
  1609> {
  1610  	pgoff_t offset = swp_offset(entry);
  1611  	struct xarray *tree = swap_zswap_tree(entry);
  1612  	unsigned long index = offset;
  1613  
  1614  	/*
  1615  	 * A pinned range is at most SWAPFILE_CLUSTER slots and is aligned to
  1616  	 * its own size, so one tree covers all of it and a single lookup is
  1617  	 * enough. Scanning only part of the range would report a false
  1618  	 * "absent" and let the caller read a stale copy from the device.
  1619  	 */
  1620  	BUILD_BUG_ON(SWAPFILE_CLUSTER > ZSWAP_ADDRESS_SPACE_PAGES);
  1621  
  1622  	return xa_find(tree, &index, offset + nr - 1, XA_PRESENT);
  1623  }
  1624  
  1625  /**
  1626   * zswap_load() - load a folio from zswap
  1627   * @folio: folio to load
  1628   *
```

## [13] P1（实现一致性）`mm/damon/ops-common.c:130` 函数 `damon_hugetlb_ptep_mkold`
- 原始特征：`pte_young|*entry`
- 卡片：消费位置 **有**（访问函数结果被使用：if (!pte_young(*entry))）；编入 -；架构依据 **有**（各架构页表项编码不同）；反证 **没有检查**（）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   105  		pfn = pmd_pfn(pmdval);
   106  	else
   107  		pfn = softleaf_to_pfn(softleaf_from_pmd(pmdval));
   108  
   109  	folio = damon_get_folio(pfn);
   110  	if (!folio)
   111  		return;
   112  
   113  	if (likely(pmd_present(pmdval)))
   114  		young |= pmdp_test_and_clear_young(vma, addr, pmd);
   115  	young |= mmu_notifier_clear_young(vma->vm_mm, addr, addr + HPAGE_PMD_SIZE);
   116  	if (young)
   117  		folio_set_young(folio);
   118  
   119  	folio_set_idle(folio);
   120  	folio_put(folio);
   121  #endif /* CONFIG_TRANSPARENT_HUGEPAGE */
   122  }
   123  
   124  #ifdef CONFIG_HUGETLB_PAGE
   125  static bool damon_hugetlb_ptep_mkold(pte_t *pte, struct mm_struct *mm,
   126  		struct vm_area_struct *vma, unsigned long addr, pte_t *entry)
   127  {
   128  	unsigned long psize = huge_page_size(hstate_vma(vma));
   129  
   130> 	if (!pte_young(*entry))
   131  		return false;
   132  	*entry = huge_ptep_get_and_clear(mm, addr, pte, psize);
   133  	*entry = pte_mkold(*entry);
   134  	set_huge_pte_at(mm, addr, pte, *entry, psize);
   135  	return true;
   136  }
   137  
   138  void damon_hugetlb_mkold(pte_t *pte, struct mm_struct *mm,
   139  		struct vm_area_struct *vma, unsigned long addr)
   140  {
   141  	bool referenced = false;
   142  	pte_t entry = huge_ptep_get(mm, addr, pte);
   143  	struct folio *folio;
   144  
   145  	folio = damon_get_monitor_folio(pte_pfn(entry));
   146  	if (!folio)
   147  		return;
   148  
   149  	referenced = damon_hugetlb_ptep_mkold(pte, mm, vma, addr, &entry);
```

## [14] WK（实现一致性）`arch/x86/kernel/perf_regs.c:267` 函数 `perf_get_regs_user`
- 原始特征：`WK|perf_get_regs_user|x86|perf_reg_abi|conditional-effect|!in_nmi()`
- 卡片：消费位置 **有**（原始特征给出了调用处或调用方依赖）；编入 x；架构依据 **有**（受影响架构：x86）；反证 **没有检查**（）
- 函数在旧版本 df2908090cda 里：有；函数体改过
```c
   242  	if (simd_enabled &&
   243  	    (mask & (REG_NOSUPPORT | PERF_REG_X86_EXT_RESERVED)))
   244  		return -EINVAL;
   245  
   246  	return 0;
   247  }
   248  
   249  u64 perf_reg_abi(struct task_struct *task)
   250  {
   251  	if (!user_64bit_mode(task_pt_regs(task)))
   252  		return PERF_SAMPLE_REGS_ABI_32;
   253  	else
   254  		return PERF_SAMPLE_REGS_ABI_64;
   255  }
   256  
   257  static DEFINE_PER_CPU(struct pt_regs, nmi_user_regs);
   258  
   259  void perf_get_regs_user(struct perf_regs *regs_user,
   260  			struct pt_regs *regs)
   261  {
   262  	struct pt_regs *regs_user_copy = this_cpu_ptr(&nmi_user_regs);
   263  	struct pt_regs *user_regs = task_pt_regs(current);
   264  
   265  	if (!in_nmi()) {
   266  		regs_user->regs = user_regs;
   267> 		regs_user->abi = perf_reg_abi(current);
   268  		return;
   269  	}
   270  
   271  	/*
   272  	 * If we're in an NMI that interrupted task_pt_regs setup, then
   273  	 * we can't sample user regs at all.  This check isn't really
   274  	 * sufficient, though, as we could be in an NMI inside an interrupt
   275  	 * that happened during task_pt_regs setup.
   276  	 */
   277  	if (regs->sp > (unsigned long)&user_regs->r11 &&
   278  	    regs->sp <= (unsigned long)(user_regs + 1)) {
   279  		regs_user->abi = PERF_SAMPLE_REGS_ABI_NONE;
   280  		regs_user->regs = NULL;
   281  		return;
   282  	}
   283  
   284  	/*
   285  	 * These registers are always saved on 64-bit syscall entry.
   286  	 * On 32-bit entry points, they are saved too except r8..r11.
```

## [15] WT（类型一致性）`arch/x86/kernel/perf_regs.c:166` 函数 `perf_simd_reg_validate`
- 原始特征：`A|assign:mask|vec_mask`
- 卡片：消费位置 **有**（assign:mask（arch/x86/kernel/perf_regs.c:166））；编入 x；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：没有（新函数）
```c
   141  					    qwords_idx - PERF_X86_YMM_QWORDS];
   142  	}
   143  
   144  	return 0;
   145  }
   146  
   147  int perf_simd_reg_validate(u16 vec_qwords, u64 vec_mask,
   148  			   u16 pred_qwords, u32 pred_mask)
   149  {
   150  	unsigned long mask;
   151  	u64 size;
   152  
   153  	if (!vec_qwords && !pred_qwords) {
   154  		if (vec_mask || pred_mask)
   155  			return -EINVAL;
   156  	}
   157  
   158  	if (vec_qwords) {
   159  		if (vec_qwords != PERF_X86_XMM_QWORDS &&
   160  		    vec_qwords != PERF_X86_YMM_QWORDS &&
   161  		    vec_qwords != PERF_X86_ZMM_QWORDS)
   162  			return -EINVAL;
   163  		if (vec_mask & ~PERF_X86_SIMD_VEC_MASK)
   164  			return -EINVAL;
   165  		/* Only full-register sampling is allowed. */
   166> 		mask = vec_mask;
   167  		if (vec_qwords == PERF_X86_XMM_QWORDS && mask &&
   168  		    !bitmap_full(&mask, PERF_X86_SIMD_XMM_REGS))
   169  			return -EINVAL;
   170  		if (vec_qwords == PERF_X86_YMM_QWORDS && mask &&
   171  		    !bitmap_full(&mask, PERF_X86_SIMD_YMM_REGS))
   172  			return -EINVAL;
   173  		if (vec_qwords == PERF_X86_ZMM_QWORDS && mask &&
   174  		    !bitmap_full(&mask, PERF_X86_SIMD_ZMM_REGS))
   175  			return -EINVAL;
   176  	}
   177  
   178  	if (pred_qwords) {
   179  		if (pred_qwords != PERF_X86_OPMASK_QWORDS)
   180  			return -EINVAL;
   181  		if (pred_mask & ~PERF_X86_SIMD_PRED_MASK)
   182  			return -EINVAL;
   183  		/* Only full-register sampling is allowed. */
   184  		mask = pred_mask;
   185  		if (pred_qwords == PERF_X86_OPMASK_QWORDS && mask &&
```

## [16] WT（类型一致性）`mm/mm_init.c:874` 函数 `init_unavailable_range`
- 原始特征：`A|return:return|online_pgcnt`
- 卡片：消费位置 **有**（return:return（mm/mm_init.c:874））；编入 rax；架构依据 **有**（32 位架构上 unsigned long 只有 32 位）；反证 **查过未见补偿**（目标类型和转换都不是 64 位）
- 函数在旧版本 df2908090cda 里：有；函数体改过
```c
   849  						   int zone, int node)
   850  {
   851  	unsigned long next_chunk_pfn __maybe_unused = spfn;
   852  	unsigned long pfn;
   853  	u64 online_pgcnt = 0, pgcnt = 0;
   854  	bool is_online = true;
   855  
   856  	for_each_valid_pfn(pfn, spfn, epfn) {
   857  		__init_single_page(pfn_to_page(pfn), pfn, zone, node);
   858  		__SetPageReserved(pfn_to_page(pfn));
   859  		pgcnt++;
   860  
   861  #ifdef CONFIG_SPARSEMEM_VMEMMAP
   862  		if (pfn >= next_chunk_pfn) {
   863  			is_online = pfn_section_valid(__pfn_to_section(pfn), pfn);
   864  			next_chunk_pfn = min(SUBSECTION_ALIGN_UP(pfn + 1), epfn);
   865  		}
   866  #endif
   867  		if (is_online)
   868  			online_pgcnt++;
   869  	}
   870  
   871  	if (pgcnt)
   872  		pr_info("On node %d, zone %s: %lld pages in unavailable ranges\n",
   873  			node, zone_names[zone], pgcnt);
   874> 	return online_pgcnt;
   875  }
   876  
   877  /*
   878   * Initially all pages are reserved - free ones are freed
   879   * up by memblock_free_all() once the early boot process is
   880   * done. Non-atomic initialization, single-pass.
   881   *
   882   * All aligned pageblocks are initialized to the specified migratetype
   883   * (usually MIGRATE_MOVABLE). Besides setting the migratetype, no related
   884   * zone stats (e.g., nr_isolate_pageblock) are touched.
   885   */
   886  void __meminit memmap_init_range(unsigned long size, int nid, unsigned long zone,
   887  		unsigned long start_pfn, unsigned long zone_end_pfn,
   888  		enum meminit_context context,
   889  		struct vmem_altmap *altmap, int migratetype,
   890  		bool isolate_pageblock)
   891  {
   892  	unsigned long pfn, end_pfn = start_pfn + size;
   893  	struct page *page;
```
