# 当前版本 df2908090cda：E-ZERO 检查前 20 条的审查材料

每条给出：检查形、组、被报实现的位置和源码、不清零路径上的条件、同组清零的实现、三个 defconfig 是否编入。
判断：确认（有隐含或显式的清零约定，被报实现在可达的正常路径上不清零，对象会交给使用者，可写成补丁）/ 可能 / 排除 / 证据不足。

## [1] E1 arch/arm/mm/dma-mapping.c:1075 arm_iommu_alloc_attrs
- 组：`ops/dma_map_ops/alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 8、不清零 5、未知 4；来源函数：__alloc_from_pool
- 清零的实现（最多 6 个）：[['arch/alpha/kernel/pci_iommu.c', 'alpha_pci_alloc_coherent'], ['arch/powerpc/kernel/dma-iommu.c', 'dma_iommu_alloc_coherent'], ['arch/powerpc/platforms/pseries/vio.c', 'vio_dma_iommu_alloc_coherent'], ['arch/sparc/kernel/iommu.c', 'dma_4u_alloc_coherent'], ['arch/sparc/kernel/pci_sun4v.c', 'dma_4v_alloc_coherent'], ['drivers/parisc/ccio-dma.c', 'ccio_alloc']]
- 不清零路径：来源 `G`，返回行 1104，最近的条件 ['!(* handle == DMA_MAPPING_ERROR)', '!(attrs & DMA_ATTR_NO_KERNEL_MAPPING)', '!(! addr)']
- 不清零路径：来源 `('C', '__iommu_alloc_simple')`，返回行 1085，最近的条件 ['coherent_flag == COHERENT || ! gfpflags_allow_blocking ( gfp )']

```c
  1073  static void *arm_iommu_alloc_attrs(struct device *dev, size_t size,
  1074  	    dma_addr_t *handle, gfp_t gfp, unsigned long attrs)
  1075  {
  1076  	pgprot_t prot = __get_dma_pgprot(attrs, PAGE_KERNEL);
  1077  	struct page **pages;
  1078  	void *addr = NULL;
  1079  	int coherent_flag = dev_dma_coherent(dev) ? COHERENT : NORMAL;
  1080  
  1081  	*handle = DMA_MAPPING_ERROR;
  1082  	size = PAGE_ALIGN(size);
  1083  
  1084  	if (coherent_flag  == COHERENT || !gfpflags_allow_blocking(gfp))
  1085  		return __iommu_alloc_simple(dev, size, gfp, handle,
  1086  					    coherent_flag, attrs);
  1087  
  1088  	pages = __iommu_alloc_buffer(dev, size, gfp, attrs, coherent_flag);
  1089  	if (!pages)
  1090  		return NULL;
  1091  
  1092  	*handle = __iommu_create_mapping(dev, pages, size, attrs);
  1093  	if (*handle == DMA_MAPPING_ERROR)
  1094  		goto err_buffer;
  1095  
  1096  	if (attrs & DMA_ATTR_NO_KERNEL_MAPPING)
  1097  		return pages;
  1098  
  1099  	addr = dma_common_pages_remap(pages, size, prot,
  1100  				   __builtin_return_address(0));
  1101  	if (!addr)
  1102  		goto err_mapping;
  1103  
  1104  	return addr;
  1105  
  1106  err_mapping:
  1107  	__iommu_remove_mapping(dev, *handle, size);
  1108  err_buffer:
  1109  	__iommu_free_buffer(dev, pages, size, attrs);
  1110  	return NULL;
  1111  }
```
来源函数 `__alloc_from_pool`：
```c
   355  static void *__alloc_from_pool(size_t size, struct page **ret_page)
   356  {
   357  	unsigned long val;
   358  	void *ptr = NULL;
   359  
   360  	if (!atomic_pool) {
   361  		WARN(1, "coherent pool not initialised!\n");
   362  		return NULL;
   363  	}
   364  
   365  	val = gen_pool_alloc(atomic_pool, size);
   366  	if (val) {
   367  		phys_addr_t phys = gen_pool_virt_to_phys(atomic_pool, val);
   368  
   369  		*ret_page = phys_to_page(phys);
   370  		ptr = (void *)val;
   371  	}
   372  
   373  	return ptr;
   374  }
```

## [2] E1 arch/powerpc/platforms/ps3/system-bus.c:508 ps3_alloc_coherent
- 组：`ops/dma_map_ops/alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 8、不清零 5、未知 4；来源函数：None
- 清零的实现（最多 6 个）：[['arch/alpha/kernel/pci_iommu.c', 'alpha_pci_alloc_coherent'], ['arch/powerpc/kernel/dma-iommu.c', 'dma_iommu_alloc_coherent'], ['arch/powerpc/platforms/pseries/vio.c', 'vio_dma_iommu_alloc_coherent'], ['arch/sparc/kernel/iommu.c', 'dma_4u_alloc_coherent'], ['arch/sparc/kernel/pci_sun4v.c', 'dma_4v_alloc_coherent'], ['drivers/parisc/ccio-dma.c', 'ccio_alloc']]
- 不清零路径：来源 `G`，返回行 534，最近的条件 ['!(! virt_addr)', '!(result)']

```c
   501  /* Allocates a contiguous real buffer and creates mappings over it.
   502   * Returns the virtual address of the buffer and sets dma_handle
   503   * to the dma address (mapping) of the first page.
   504   */
   505  static void * ps3_alloc_coherent(struct device *_dev, size_t size,
   506  				 dma_addr_t *dma_handle, gfp_t flag,
   507  				 unsigned long attrs)
   508  {
   509  	int result;
   510  	struct ps3_system_bus_device *dev = ps3_dev_to_system_bus_dev(_dev);
   511  	unsigned long virt_addr;
   512  
   513  	flag &= ~(__GFP_DMA | __GFP_HIGHMEM);
   514  	flag |= __GFP_ZERO;
   515  
   516  	virt_addr = __get_free_pages(flag, get_order(size));
   517  
   518  	if (!virt_addr) {
   519  		pr_debug("%s:%d: get_free_pages failed\n", __func__, __LINE__);
   520  		goto clean_none;
   521  	}
   522  
   523  	result = ps3_dma_map(dev->d_region, virt_addr, size, dma_handle,
   524  			     CBE_IOPTE_PP_W | CBE_IOPTE_PP_R |
   525  			     CBE_IOPTE_SO_RW | CBE_IOPTE_M);
   526  
   527  	if (result) {
   528  		pr_debug("%s:%d: ps3_dma_map failed (%d)\n",
   529  			__func__, __LINE__, result);
   530  		BUG_ON("check region type");
   531  		goto clean_alloc;
   532  	}
   533  
   534  	return (void*)virt_addr;
   535  
   536  clean_alloc:
   537  	free_pages(virt_addr, get_order(size));
   538  clean_none:
   539  	dma_handle = NULL;
   540  	return NULL;
   541  }
```

## [3] E1 arch/powerpc/platforms/pseries/ibmebus.c:73 ibmebus_alloc_coherent
- 组：`ops/dma_map_ops/alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 8、不清零 5、未知 4；来源函数：None
- 清零的实现（最多 6 个）：[['arch/alpha/kernel/pci_iommu.c', 'alpha_pci_alloc_coherent'], ['arch/powerpc/kernel/dma-iommu.c', 'dma_iommu_alloc_coherent'], ['arch/powerpc/platforms/pseries/vio.c', 'vio_dma_iommu_alloc_coherent'], ['arch/sparc/kernel/iommu.c', 'dma_4u_alloc_coherent'], ['arch/sparc/kernel/pci_sun4v.c', 'dma_4v_alloc_coherent'], ['drivers/parisc/ccio-dma.c', 'ccio_alloc']]
- 不清零路径：来源 `G`，返回行 79，最近的条件 []

```c
    68  static void *ibmebus_alloc_coherent(struct device *dev,
    69  				    size_t size,
    70  				    dma_addr_t *dma_handle,
    71  				    gfp_t flag,
    72  				    unsigned long attrs)
    73  {
    74  	void *mem;
    75  
    76  	mem = kmalloc(size, flag);
    77  	*dma_handle = (dma_addr_t)mem;
    78  
    79  	return mem;
    80  }
```

## [4] E1 drivers/xen/grant-dma-ops.c:81 xen_grant_dma_alloc
- 组：`ops/dma_map_ops/alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 8、不清零 5、未知 4；来源函数：None
- 清零的实现（最多 6 个）：[['arch/alpha/kernel/pci_iommu.c', 'alpha_pci_alloc_coherent'], ['arch/powerpc/kernel/dma-iommu.c', 'dma_iommu_alloc_coherent'], ['arch/powerpc/platforms/pseries/vio.c', 'vio_dma_iommu_alloc_coherent'], ['arch/sparc/kernel/iommu.c', 'dma_4u_alloc_coherent'], ['arch/sparc/kernel/pci_sun4v.c', 'dma_4v_alloc_coherent'], ['drivers/parisc/ccio-dma.c', 'ccio_alloc']]
- 不清零路径：来源 `G`，返回行 113，最近的条件 ['!(unlikely ( data -> broken ))', '!(! ret)', '!(gnttab_alloc_grant_reference_seq ( n_pages , & grant ))']

```c
    73   * DMA addresses.
    74   * Such a DMA address is formed by using the grant reference as a frame
    75   * number and setting the highest address bit (this bit is for the backend
    76   * to be able to distinguish it from e.g. a mmio address).
    77   */
    78  static void *xen_grant_dma_alloc(struct device *dev, size_t size,
    79  				 dma_addr_t *dma_handle, gfp_t gfp,
    80  				 unsigned long attrs)
    81  {
    82  	struct xen_grant_dma_data *data;
    83  	unsigned int i, n_pages = XEN_PFN_UP(size);
    84  	unsigned long pfn;
    85  	grant_ref_t grant;
    86  	void *ret;
    87  
    88  	data = find_xen_grant_dma_data(dev);
    89  	if (!data)
    90  		return NULL;
    91  
    92  	if (unlikely(data->broken))
    93  		return NULL;
    94  
    95  	ret = alloc_pages_exact(n_pages * XEN_PAGE_SIZE, gfp);
    96  	if (!ret)
    97  		return NULL;
    98  
    99  	pfn = virt_to_pfn(ret);
   100  
   101  	if (gnttab_alloc_grant_reference_seq(n_pages, &grant)) {
   102  		free_pages_exact(ret, n_pages * XEN_PAGE_SIZE);
   103  		return NULL;
   104  	}
   105  
   106  	for (i = 0; i < n_pages; i++) {
   107  		gnttab_grant_foreign_access_ref(grant + i, data->backend_domid,
   108  				pfn_to_gfn(pfn + i), 0);
   109  	}
   110  
   111  	*dma_handle = grant_to_dma(grant);
   112  
   113  	return ret;
   114  }
```

## [5] E1 kernel/dma/direct.c:204 dma_direct_alloc
- 组：`ops/dma_map_ops/alloc`；架构证据：True；编入：{'riscv': True, 'arm64': True, 'x86_64': True}
- 组里：清零 8、不清零 5、未知 4；来源函数：__dma_direct_alloc_pages
- 清零的实现（最多 6 个）：[['arch/alpha/kernel/pci_iommu.c', 'alpha_pci_alloc_coherent'], ['arch/powerpc/kernel/dma-iommu.c', 'dma_iommu_alloc_coherent'], ['arch/powerpc/platforms/pseries/vio.c', 'vio_dma_iommu_alloc_coherent'], ['arch/sparc/kernel/iommu.c', 'dma_4u_alloc_coherent'], ['arch/sparc/kernel/pci_sun4v.c', 'dma_4v_alloc_coherent'], ['drivers/parisc/ccio-dma.c', 'ccio_alloc']]
- 不清零路径：来源 `('C', 'dma_direct_alloc_no_mapping')`，返回行 231，最近的条件 ['attrs & __DMA_ATTR_ALLOC_CC_SHARED', 'attrs & DMA_ATTR_NO_WARN', '( ( attrs & ( DMA_ATTR_NO_KERNEL_MAPPING | __DMA_ATTR_ALLOC_CC_SHARED ) ) == DMA']

```c
   202  void *dma_direct_alloc(struct device *dev, size_t size,
   203  		dma_addr_t *dma_handle, gfp_t gfp, unsigned long attrs)
   204  {
   205  	bool remap = false, set_uncached = false;
   206  	bool mark_mem_decrypt = false;
   207  	bool allow_highmem = true;
   208  	struct page *page;
   209  	void *cpu_addr;
   210  
   211  	if (force_dma_unencrypted(dev))
   212  		attrs |= __DMA_ATTR_ALLOC_CC_SHARED;
   213  
   214  	if (attrs & __DMA_ATTR_ALLOC_CC_SHARED) {
   215  		/*
   216  		 * Unencrypted/shared DMA requires a linear-mapped buffer
   217  		 * address to look up the PFN and set architecture-required PFN
   218  		 * attributes. This is not possible with HighMem. Avoid HighMem
   219  		 * allocation.
   220  		 */
   221  		allow_highmem = false;
   222  		mark_mem_decrypt = true;
   223  	}
   224  
   225  	size = PAGE_ALIGN(size);
   226  	if (attrs & DMA_ATTR_NO_WARN)
   227  		gfp |= __GFP_NOWARN;
   228  
   229  	if (((attrs & (DMA_ATTR_NO_KERNEL_MAPPING | __DMA_ATTR_ALLOC_CC_SHARED)) ==
   230  	     DMA_ATTR_NO_KERNEL_MAPPING) && !is_swiotlb_for_alloc(dev))
   231  		return dma_direct_alloc_no_mapping(dev, size, dma_handle, gfp);
   232  
   233  	if (!dev_is_dma_coherent(dev)) {
   234  		if (IS_ENABLED(CONFIG_ARCH_HAS_DMA_ALLOC) &&
   235  		    !is_swiotlb_for_alloc(dev))
   236  			return arch_dma_alloc(dev, size, dma_handle, gfp,
   237  					      attrs);
   238  
   239  		/*
   240  		 * If there is a global pool, always allocate from it for
   241  		 * non-coherent devices.
   242  		 */
   243  		if (IS_ENABLED(CONFIG_DMA_GLOBAL_POOL))
   244  			return dma_alloc_from_global_coherent(dev, size,
   245  					dma_handle);
   246  
   247  		/*
   248  		 * Otherwise we require the architecture to either be able to
   249  		 * mark arbitrary parts of the kernel direct mapping uncached,
   250  		 * or remapped it uncached.
   251  		 */
   252  		set_uncached = IS_ENABLED(CONFIG_ARCH_HAS_DMA_SET_UNCACHED);
   253  		remap = IS_ENABLED(CONFIG_DMA_DIRECT_REMAP);
   254  		if (!set_uncached && !remap) {
   255  			pr_warn_once("coherent DMA allocations not supported on this platform.\n");
   256  			return NULL;
   257  		}
   258  	}
   259  
   260  	/*
   261  	 * Remapping or decrypting memory may block, allocate the memory from
   262  	 * the atomic pools instead if we aren't allowed block.
   263  	 * FIXME: With CONFIG_DMA_DIRECT_REMAP, the pool is also mapped as
   264  	 * DMA-coherent (non-cacheable). We may want to create a separate pool
   265  	 * dedicated to CC_SHARED atomic allocations.
   266  	 */
   267  	if ((remap || (attrs & __DMA_ATTR_ALLOC_CC_SHARED)) &&
   268  	    dma_direct_use_pool(dev, gfp)) {
   269  		page = dma_direct_alloc_from_pool(dev, size,
   270  					dma_handle, &cpu_addr,
   271  					gfp, attrs);
        ...（共 156 行，后略）
```
来源函数 `__dma_direct_alloc_pages`：
```c
   117  static struct page *__dma_direct_alloc_pages(struct device *dev, size_t size,
   118  		gfp_t gfp, bool allow_highmem)
   119  {
   120  	int node = dev_to_node(dev);
   121  	struct page *page;
   122  	u64 phys_limit;
   123  
   124  	WARN_ON_ONCE(!PAGE_ALIGNED(size));
   125  
   126  	gfp |= dma_direct_optimal_gfp_mask(dev, &phys_limit);
   127  	page = dma_alloc_contiguous(dev, size, gfp);
   128  	if (page) {
   129  		if (dma_coherent_ok(dev, page_to_phys(page), size) &&
   130  		    (allow_highmem || !PageHighMem(page)))
   131  			return page;
   132  
   133  		dma_free_contiguous(dev, page, size);
   134  	}
   135  
   136  	while ((page = alloc_pages_node(node, gfp, get_order(size)))
   137  	       && !dma_coherent_ok(dev, page_to_phys(page), size)) {
   138  		__free_pages(page, get_order(size));
   139  
   140  		if (IS_ENABLED(CONFIG_ZONE_DMA32) &&
   141  		    phys_limit < DMA_BIT_MASK(64) &&
   142  		    !(gfp & (GFP_DMA32 | GFP_DMA)))
   143  			gfp |= GFP_DMA32;
   144  		else if (IS_ENABLED(CONFIG_ZONE_DMA) && !(gfp & GFP_DMA))
   145  			gfp = (gfp & ~GFP_DMA32) | GFP_DMA;
   146  		else
   147  			return NULL;
   148  	}
   149  
   150  	return page;
   151  }
```

## [6] E1 net/netfilter/xt_hashlimit.c:1072 dl_seq_start
- 组：`ops/seq_operations/start`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 4、不清零 1、未知 293；来源函数：None
- 清零的实现（最多 6 个）：[['arch/x86/mm/pat/memtype.c', 'memtype_seq_start'], ['drivers/net/wireless/intel/iwlwifi/fw/debugfs.c', 'iwl_dbgfs_fw_info_seq_start'], ['drivers/s390/cio/blacklist.c', 'cio_ignore_proc_seq_start'], ['mm/vmstat.c', 'vmstat_start']]
- 不清零路径：来源 `R`，返回行 1085，最近的条件 ['!(* pos >= htable -> cfg . size)', '!(! bucket)']

```c
  1069  /* PROC stuff */
  1070  static void *dl_seq_start(struct seq_file *s, loff_t *pos)
  1071  	__acquires(htable->lock)
  1072  {
  1073  	struct xt_hashlimit_htable *htable = pde_data(file_inode(s->file));
  1074  	unsigned int *bucket;
  1075  
  1076  	spin_lock_bh(&htable->lock);
  1077  	if (*pos >= htable->cfg.size)
  1078  		return NULL;
  1079  
  1080  	bucket = kmalloc(sizeof(unsigned int), GFP_ATOMIC);
  1081  	if (!bucket)
  1082  		return ERR_PTR(-ENOMEM);
  1083  
  1084  	*bucket = *pos;
  1085  	return bucket;
  1086  }
```

## [7] E1 arch/arm64/mm/pgd.c:32 pgd_alloc
- 组：`name/pgd_alloc`；架构证据：True；编入：{'riscv': False, 'arm64': True, 'x86_64': False}
- 组里：清零 4、不清零 3、未知 17；来源函数：None
- 清零的实现（最多 6 个）：[['arch/m68k/include/asm/mcf_pgalloc.h', 'pgd_alloc'], ['arch/m68k/include/asm/sun3_pgalloc.h', 'pgd_alloc'], ['arch/openrisc/include/asm/pgalloc.h', 'pgd_alloc'], ['arch/powerpc/include/asm/book3s/64/pgalloc.h', 'pgd_alloc']]
- 不清零路径：来源 `R`，返回行 38，最近的条件 ['!(pgdir_is_page_size ( ))']

```c
    31  pgd_t *pgd_alloc(struct mm_struct *mm)
    32  {
    33  	gfp_t gfp = GFP_PGTABLE_USER;
    34  
    35  	if (pgdir_is_page_size())
    36  		return __pgd_alloc(mm, 0);
    37  	else
    38  		return kmem_cache_alloc(pgd_cache, gfp);
    39  }
```

## [8] E1 arch/sh/mm/pgtable.c:35 pgd_alloc
- 组：`name/pgd_alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 4、不清零 3、未知 17；来源函数：None
- 清零的实现（最多 6 个）：[['arch/m68k/include/asm/mcf_pgalloc.h', 'pgd_alloc'], ['arch/m68k/include/asm/sun3_pgalloc.h', 'pgd_alloc'], ['arch/openrisc/include/asm/pgalloc.h', 'pgd_alloc'], ['arch/powerpc/include/asm/book3s/64/pgalloc.h', 'pgd_alloc']]
- 不清零路径：来源 `R`，返回行 36，最近的条件 []

```c
    34  pgd_t *pgd_alloc(struct mm_struct *mm)
    35  {
    36  	return kmem_cache_alloc(pgd_cachep, GFP_KERNEL);
    37  }
```

## [9] E1 arch/sparc/include/asm/pgalloc_64.h:27 pgd_alloc
- 组：`name/pgd_alloc`；架构证据：True；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 4、不清零 3、未知 17；来源函数：None
- 清零的实现（最多 6 个）：[['arch/m68k/include/asm/mcf_pgalloc.h', 'pgd_alloc'], ['arch/m68k/include/asm/sun3_pgalloc.h', 'pgd_alloc'], ['arch/openrisc/include/asm/pgalloc.h', 'pgd_alloc'], ['arch/powerpc/include/asm/book3s/64/pgalloc.h', 'pgd_alloc']]
- 不清零路径：来源 `R`，返回行 28，最近的条件 []

```c
    26  static inline pgd_t *pgd_alloc(struct mm_struct *mm)
    27  {
    28  	return kmem_cache_alloc(pgtable_cache, GFP_KERNEL);
    29  }
```

## [10] E3 mm/dmapool.c:409 dma_pool_alloc
- 组：`name/dma_pool_alloc`；架构证据：False；编入：{'riscv': True, 'arm64': True, 'x86_64': True}
- 调用方：['drivers/dma/ioat/prep.c', 'ioat3_alloc_sed', 90]（调用方去掉了 __GFP_ZERO：False）
- 提前返回：行 440，条件 ['!(! block)', '!(want_init_on_alloc ( mem_flags ))']

```c
   401   * @handle: pointer to dma address of block
   402   *
   403   * Return: the kernel virtual address of a currently unused block,
   404   * and reports its dma address through the handle.
   405   * If such a memory block can't be allocated, %NULL is returned.
   406   */
   407  void *dma_pool_alloc(struct dma_pool *pool, gfp_t mem_flags,
   408  		     dma_addr_t *handle)
   409  {
   410  	struct dma_block *block;
   411  	struct dma_page *page;
   412  	unsigned long flags;
   413  
   414  	might_alloc(mem_flags);
   415  
   416  	spin_lock_irqsave(&pool->lock, flags);
   417  	block = pool_block_pop(pool);
   418  	if (!block) {
   419  		/*
   420  		 * pool_alloc_page() might sleep, so temporarily drop
   421  		 * &pool->lock
   422  		 */
   423  		spin_unlock_irqrestore(&pool->lock, flags);
   424  
   425  		page = pool_alloc_page(pool, mem_flags & (~__GFP_ZERO));
   426  		if (!page)
   427  			return NULL;
   428  
   429  		spin_lock_irqsave(&pool->lock, flags);
   430  		pool_initialise_page(pool, page);
   431  		block = pool_block_pop(pool);
   432  	}
   433  	spin_unlock_irqrestore(&pool->lock, flags);
   434  
   435  	*handle = block->dma;
   436  	pool_check_block(pool, block, mem_flags);
   437  	if (want_init_on_alloc(mem_flags))
   438  		memset(block, 0, pool->size);
   439  
   440  	return block;
   441  }
```

## [11] E3 mm/util.c:1090 mem_dump_obj
- 组：`name/mem_dump_obj`；架构证据：False；编入：{'riscv': True, 'arm64': True, 'x86_64': True}
- 调用方：['kernel/rcu/rcutorture.c', 'rcu_torture_mem_dump_obj', 3148]（调用方去掉了 __GFP_ZERO：False）
- 提前返回：行 1111，条件 ['!(is_vmalloc_addr ( object ))', '!(virt_addr_valid ( object ))', 'object == NULL']
- 提前返回：行 1111，条件 ['!(kmem_dump_obj ( object ))', '!(vmalloc_dump_obj ( object ))', 'is_vmalloc_addr ( object )']
- 提前返回：行 1097，条件 ['!(kmem_dump_obj ( object ))', 'vmalloc_dump_obj ( object )']

```c
  1082   * This function uses pr_cont(), so that the caller is expected to have
  1083   * printed out whatever preamble is appropriate.  The provenance information
  1084   * depends on the type of object and on how much debugging is enabled.
  1085   * For example, for a slab-cache object, the slab name is printed, and,
  1086   * if available, the return address and stack trace from the allocation
  1087   * and last free path of that object.
  1088   */
  1089  void mem_dump_obj(void *object)
  1090  {
  1091  	const char *type;
  1092  
  1093  	if (kmem_dump_obj(object))
  1094  		return;
  1095  
  1096  	if (vmalloc_dump_obj(object))
  1097  		return;
  1098  
  1099  	if (is_vmalloc_addr(object))
  1100  		type = "vmalloc memory";
  1101  	else if (virt_addr_valid(object))
  1102  		type = "non-slab/vmalloc memory";
  1103  	else if (object == NULL)
  1104  		type = "NULL pointer";
  1105  	else if (object == ZERO_SIZE_PTR)
  1106  		type = "zero-size pointer";
  1107  	else
  1108  		type = "non-paged memory";
  1109  
  1110  	pr_cont(" %s\n", type);
  1111  }
```

## [12] E1 drivers/gpu/drm/drm_atomic_helper.c:4135 drm_atomic_helper_bridge_get_hdmi_output_bus_fmts
- 组：`ops/drm_bridge_funcs/atomic_get_output_bus_fmts`；架构证据：False；编入：{'riscv': True, 'arm64': True, 'x86_64': True}
- 组里：清零 7、不清零 1、未知 8；来源函数：None
- 清零的实现（最多 6 个）：[['drivers/gpu/drm/bridge/ite-it66121.c', 'it66121_bridge_atomic_get_output_bus_fmts'], ['drivers/gpu/drm/bridge/synopsys/dw-dp.c', 'dw_dp_bridge_atomic_get_output_bus_fmts'], ['drivers/gpu/drm/bridge/synopsys/dw-hdmi.c', 'dw_hdmi_bridge_atomic_get_output_bus_fmts'], ['drivers/gpu/drm/bridge/tc358767.c', 'tc_edp_atomic_get_output_bus_fmts'], ['drivers/gpu/drm/mediatek/mtk_dpi.c', 'mtk_dpi_bridge_atomic_get_output_bus_fmts'], ['drivers/gpu/drm/verisilicon/vs_bridge.c', 'vs_bridge_atomic_get_output_bus_fmts_dp']]
- 不清零路径：来源 `R`，返回行 4187，最近的条件 ['!(bridge -> supported_formats & BIT ( DRM_OUTPUT_COLOR_FORMAT_YCBCR444 ))', '!(bridge -> supported_formats & BIT ( DRM_OUTPUT_COLOR_FORMAT_YCBCR422 ))', '!(bridge -> supported_formats & BIT ( DRM_OUTPUT_COLOR_FORMAT_YCBCR420 ))']

```c
  4127   * chosen HDMI output bits per compoennt, or %NULL if it fails to allocate one.
  4128   */
  4129  u32 *
  4130  drm_atomic_helper_bridge_get_hdmi_output_bus_fmts(struct drm_bridge *bridge,
  4131  					struct drm_bridge_state *bridge_state,
  4132  					struct drm_crtc_state *crtc_state,
  4133  					struct drm_connector_state *conn_state,
  4134  					unsigned int *num_output_fmts)
  4135  {
  4136  	unsigned int num_fmts = 0;
  4137  	u32 *out_fmts;
  4138  
  4139  	/*
  4140  	 * bridge->supported_formats is a bit field of BIT(enum drm_output_color_format)
  4141  	 * values. The smallest hweight that is smaller than or equal to
  4142  	 * %DRM_OUTPUT_COLOR_FORMAT_COUNT will do for counting set bits here.
  4143  	 */
  4144  	BUILD_BUG_ON(const_true(DRM_OUTPUT_COLOR_FORMAT_COUNT > 8));
  4145  	out_fmts = kmalloc_array(hweight8(bridge->supported_formats),
  4146  				 sizeof(u32), GFP_KERNEL);
  4147  	if (!out_fmts) {
  4148  		*num_output_fmts = 0;
  4149  		return NULL;
  4150  	}
  4151  
  4152  	switch (conn_state->hdmi.output_bpc) {
  4153  	case 12:
  4154  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_RGB444))
  4155  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_RGB121212_1X36;
  4156  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR444))
  4157  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_YUV12_1X36;
  4158  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR422))
  4159  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYVY12_1X24;
  4160  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR420))
  4161  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYYVYY12_0_5X36;
  4162  		break;
  4163  	case 10:
  4164  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_RGB444))
  4165  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_RGB101010_1X30;
  4166  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR444))
  4167  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_YUV10_1X30;
  4168  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR422))
  4169  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYVY10_1X20;
  4170  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR420))
  4171  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYYVYY10_0_5X30;
  4172  		break;
  4173  	default:
  4174  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_RGB444))
  4175  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_RGB888_1X24;
  4176  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR444))
  4177  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_YUV8_1X24;
  4178  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR422))
  4179  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYVY8_1X16;
  4180  		if (bridge->supported_formats & BIT(DRM_OUTPUT_COLOR_FORMAT_YCBCR420))
  4181  			out_fmts[num_fmts++] = MEDIA_BUS_FMT_UYYVYY8_0_5X24;
  4182  		break;
  4183  	}
  4184  
  4185  	*num_output_fmts = num_fmts;
  4186  
  4187  	return out_fmts;
  4188  }
```

## [13] E1 drivers/message/fusion/mptscsih.c:1268 mptscsih_info
- 组：`ops/scsi_host_template/info`；架构证据：False；编入：{'riscv': False, 'arm64': False, 'x86_64': False}
- 组里：清零 6、不清零 1、未知 25；来源函数：None
- 清零的实现（最多 6 个）：[['drivers/scsi/aic7xxx/aic79xx_osm.c', 'ahd_linux_info'], ['drivers/scsi/aic7xxx/aic7xxx_osm.c', 'ahc_linux_info'], ['drivers/scsi/bfa/bfad_im.c', 'bfad_im_info'], ['drivers/scsi/ips.c', 'ips_info'], ['drivers/scsi/lpfc/lpfc_scsi.c', 'lpfc_info'], ['drivers/scsi/qla1280.c', 'qla1280_info']]
- 不清零路径：来源 `R`，返回行 1282，最近的条件 ['h -> info_kbuf == NULL', '!(( h -> info_kbuf = kmalloc ( 0x1000 , GFP_KERNEL ) ) == NULL)']
- 不清零路径：来源 `R`，返回行 1276，最近的条件 ['h -> info_kbuf == NULL', '( h -> info_kbuf = kmalloc ( 0x1000 , GFP_KERNEL ) ) == NULL']

```c
  1260   *	@SChost: Pointer to Scsi_Host structure
  1261   *
  1262   *	(linux scsi_host_template.info routine)
  1263   *
  1264   *	Returns pointer to buffer where information was written.
  1265   */
  1266  const char *
  1267  mptscsih_info(struct Scsi_Host *SChost)
  1268  {
  1269  	MPT_SCSI_HOST *h;
  1270  	int size = 0;
  1271  
  1272  	h = shost_priv(SChost);
  1273  
  1274  	if (h->info_kbuf == NULL)
  1275  		if ((h->info_kbuf = kmalloc(0x1000 /* 4Kb */, GFP_KERNEL)) == NULL)
  1276  			return h->info_kbuf;
  1277  	h->info_kbuf[0] = '\0';
  1278  
  1279  	mpt_print_ioc_summary(h->ioc, h->info_kbuf, &size, 0, 0);
  1280  	h->info_kbuf[size-1] = '\0';
  1281  
  1282  	return h->info_kbuf;
  1283  }
```
