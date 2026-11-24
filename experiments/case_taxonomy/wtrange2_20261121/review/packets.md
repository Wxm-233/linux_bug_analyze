# WT 盲审材料（wtrange2，24 条）

每条回答两件事：(1) 在 32 位构建上，这次转换的值是否**一定放得下**（是 / 否 / 说不清）；(2) 它是不是完整线索（完整线索 / 未决 / 排除 / 未知，排除写原因类别）。
源码版本 `df2908090cda`，行号前的 `>` 标出报告行。“32 位构建”一栏列出编入了该文件的窄目标构建（rv32 有 MMU、rv32 无 MMU、i386 defconfig、i386 allmodconfig）。

## [1] `kernel/events/uprobes.c:147` 函数 `offset_to_vaddr`
- 原始特征：`A|return:return|vma->vm_start+offset-((loff_t)vma_start_pgoff(vma)<<PAGE_SHIFT)`
- 32 位构建：i386, i386_allmod, rv32_abi
```c
   122  static void uprobe_warn(struct task_struct *t, const char *msg)
   123  {
   124  	pr_warn("uprobe: %s:%d failed to %s\n", t->comm, t->pid, msg);
   125  }
   126  
   127  /*
   128   * valid_vma: Verify if the specified vma is an executable vma
   129   * Relax restrictions while unregistering: vm_flags might have
   130   * changed after breakpoint was inserted.
   131   *	- is_register: indicates if we are in register context.
   132   *	- Return 1 if the specified virtual address is in an
   133   *	  executable vma.
   134   */
   135  static bool valid_vma(struct vm_area_struct *vma, bool is_register)
   136  {
   137  	vm_flags_t flags = VM_HUGETLB | VM_MAYEXEC | VM_MAYSHARE;
   138  
   139  	if (is_register)
   140  		flags |= VM_WRITE;
   141  
   142  	return vma->vm_file && (vma->vm_flags & flags) == VM_MAYEXEC;
   143  }
   144  
   145  static unsigned long offset_to_vaddr(struct vm_area_struct *vma, loff_t offset)
   146  {
   147> 	return vma->vm_start + offset -
   148  		((loff_t)vma_start_pgoff(vma) << PAGE_SHIFT);
   149  }
   150  
   151  static loff_t vaddr_to_offset(struct vm_area_struct *vma, unsigned long vaddr)
   152  {
   153  	return ((loff_t)vma_start_pgoff(vma) << PAGE_SHIFT) +
   154  		(vaddr - vma->vm_start);
   155  }
   156  
   157  /**
   158   * is_swbp_insn - check if instruction is breakpoint instruction.
```

## [2] `fs/btrfs/verity.c:360` 函数 `read_key_bytes`
- 原始特征：`A|assign:copy_bytes|copy_end-offset`
- 32 位构建：i386_allmod
```c
   335  		if (copied > 0) {
   336  			/*
   337  			 * Once we've copied something, we want all of the items
   338  			 * to be sequential
   339  			 */
   340  			if (key.offset != offset)
   341  				break;
   342  		} else {
   343  			/*
   344  			 * Our initial offset might be in the middle of an
   345  			 * item.  Make sure it all makes sense.
   346  			 */
   347  			if (key.offset > offset)
   348  				break;
   349  			if (item_end <= offset)
   350  				break;
   351  		}
   352  
   353  		/* desc = NULL to just sum all the item lengths */
   354  		if (!dest)
   355  			copy_end = item_end;
   356  		else
   357  			copy_end = min(offset + len, item_end);
   358  
   359  		/* Number of bytes in this item we want to copy */
   360> 		copy_bytes = copy_end - offset;
   361  
   362  		/* Offset from the start of item for copying */
   363  		copy_offset = offset - key.offset;
   364  
   365  		if (dest) {
   366  			if (dest_folio)
   367  				kaddr = kmap_local_folio(dest_folio, 0);
   368  
   369  			data = btrfs_item_ptr(leaf, path->slots[0], void);
   370  			read_extent_buffer(leaf, kaddr + dest_offset,
   371  					   (unsigned long)data + copy_offset,
```

## [3] `fs/udf/inode.c:454` 函数 `udf_expand_file_adinicb`
- 原始特征：`A|arg:memcpy_from_folio#3|inode->i_size`
- 32 位构建：i386_allmod
```c
   429  	if (!folio_test_uptodate(folio))
   430  		udf_adinicb_read_folio(folio);
   431  	down_write(&iinfo->i_data_sem);
   432  	memset(iinfo->i_data + iinfo->i_lenEAttr, 0x00,
   433  	       iinfo->i_lenAlloc);
   434  	iinfo->i_lenAlloc = 0;
   435  	if (UDF_QUERY_FLAG(inode->i_sb, UDF_FLAG_USE_SHORT_AD))
   436  		iinfo->i_alloc_type = ICBTAG_FLAG_AD_SHORT;
   437  	else
   438  		iinfo->i_alloc_type = ICBTAG_FLAG_AD_LONG;
   439  	up_write(&iinfo->i_data_sem);
   440  
   441  	/* Allocate the block underlying the data */
   442  	err = udf_map_block(inode, &map);
   443  	if (err < 0)
   444  		goto restore;
   445  
   446  	folio_mark_dirty(folio);
   447  	folio_unlock(folio);
   448  	err = filemap_fdatawrite(inode->i_mapping);
   449  	if (err) {
   450  		/* Restore everything back so that we don't lose data... */
   451  		folio_lock(folio);
   452  restore:
   453  		down_write(&iinfo->i_data_sem);
   454> 		memcpy_from_folio(iinfo->i_data + iinfo->i_lenEAttr,
   455  				folio, 0, inode->i_size);
   456  		iinfo->i_alloc_type = ICBTAG_FLAG_AD_IN_ICB;
   457  		iinfo->i_lenAlloc = inode->i_size;
   458  		up_write(&iinfo->i_data_sem);
   459  		folio_unlock(folio);
   460  	}
   461  	folio_put(folio);
   462  	mark_inode_dirty(inode);
   463  
   464  	return err;
   465  }
```

## [4] `arch/mips/kernel/setup.c:468` 函数 `mips_parse_crashkernel`
- 原始特征：`A|arg:memblock_phys_alloc_range#0|crash_size`
- 32 位构建：无
```c
   443  	memblock_reserve(elfcorehdr_addr, elfcorehdr_size);
   444  #endif
   445  }
   446  
   447  /* 64M alignment for crash kernel regions */
   448  #define CRASH_ALIGN	SZ_64M
   449  #define CRASH_ADDR_MAX	SZ_512M
   450  
   451  static void __init mips_parse_crashkernel(void)
   452  {
   453  	unsigned long long total_mem;
   454  	unsigned long long crash_size, crash_base;
   455  	int ret;
   456  
   457  	if (!IS_ENABLED(CONFIG_CRASH_RESERVE))
   458  		return;
   459  
   460  	total_mem = memblock_phys_mem_size();
   461  	ret = parse_crashkernel(boot_command_line, total_mem,
   462  				&crash_size, &crash_base,
   463  				NULL, NULL, NULL);
   464  	if (ret != 0 || crash_size <= 0)
   465  		return;
   466  
   467  	if (crash_base <= 0) {
   468> 		crash_base = memblock_phys_alloc_range(crash_size, CRASH_ALIGN,
   469  						       CRASH_ALIGN,
   470  						       CRASH_ADDR_MAX);
   471  		if (!crash_base) {
   472  			pr_warn("crashkernel reservation failed - No suitable area found.\n");
   473  			return;
   474  		}
   475  	} else {
   476  		unsigned long long start;
   477  
   478  		start = memblock_phys_alloc_range(crash_size, 1,
   479  						  crash_base,
```

## [5] `arch/x86/kernel/ksysfs.c:314` 函数 `get_setup_data_total_num`
- 原始特征：`A|arg:memremap#0|pa_data`
- 32 位构建：i386, i386_allmod
```c
   289  	ret = sysfs_create_group(kobj, &setup_data_attr_group);
   290  	if (ret)
   291  		goto out_kobj;
   292  	*kobjp = kobj;
   293  
   294  	return 0;
   295  out_kobj:
   296  	kobject_put(kobj);
   297  	return ret;
   298  }
   299  
   300  static void __init cleanup_setup_data_node(struct kobject *kobj)
   301  {
   302  	sysfs_remove_group(kobj, &setup_data_attr_group);
   303  	kobject_put(kobj);
   304  }
   305  
   306  static int __init get_setup_data_total_num(u64 pa_data, int *nr)
   307  {
   308  	int ret = 0;
   309  	struct setup_data *data;
   310  
   311  	*nr = 0;
   312  	while (pa_data) {
   313  		*nr += 1;
   314> 		data = memremap(pa_data, sizeof(*data), MEMREMAP_WB);
   315  		if (!data) {
   316  			ret = -ENOMEM;
   317  			goto out;
   318  		}
   319  		pa_data = data->next;
   320  		memunmap(data);
   321  	}
   322  
   323  out:
   324  	return ret;
   325  }
```

## [6] `fs/udf/inode.c:218` 函数 `udf_adinicb_read_folio`
- 原始特征：`A|arg:folio_fill_tail#3|isize`
- 32 位构建：i386_allmod
```c
   193  	 * conversion.
   194  	 */
   195  	if (iinfo->i_alloc_type != ICBTAG_FLAG_AD_IN_ICB)
   196  		return 1;
   197  
   198  	memcpy_from_file_folio(iinfo->i_data + iinfo->i_lenEAttr, folio,
   199  				0, i_size_read(inode));
   200  	folio_unlock(folio);
   201  	mark_inode_dirty(inode);
   202  	return 0;
   203  }
   204  
   205  static int udf_writepages(struct address_space *mapping,
   206  			  struct writeback_control *wbc)
   207  {
   208  	return __mpage_writepages(mapping, wbc, udf_get_block_wb,
   209  				  udf_handle_page_wb);
   210  }
   211  
   212  static void udf_adinicb_read_folio(struct folio *folio)
   213  {
   214  	struct inode *inode = folio->mapping->host;
   215  	struct udf_inode_info *iinfo = UDF_I(inode);
   216  	loff_t isize = i_size_read(inode);
   217  
   218> 	folio_fill_tail(folio, 0, iinfo->i_data + iinfo->i_lenEAttr, isize);
   219  	folio_mark_uptodate(folio);
   220  }
   221  
   222  static int udf_read_folio(struct file *file, struct folio *folio)
   223  {
   224  	struct udf_inode_info *iinfo = UDF_I(file_inode(file));
   225  
   226  	if (iinfo->i_alloc_type == ICBTAG_FLAG_AD_IN_ICB) {
   227  		udf_adinicb_read_folio(folio);
   228  		folio_unlock(folio);
   229  		return 0;
```

## [7] `kernel/cgroup/dmem.c:739` 函数 `dmem_cgroup_try_charge`
- 原始特征：`A|arg:page_counter_try_charge#1|size`
- 32 位构建：i386_allmod
```c
   714  int dmem_cgroup_try_charge(struct dmem_cgroup_region *region, u64 size,
   715  			  struct dmem_cgroup_pool_state **ret_pool,
   716  			  struct dmem_cgroup_pool_state **ret_limit_pool)
   717  {
   718  	struct dmemcg_state *cg;
   719  	struct dmem_cgroup_pool_state *pool;
   720  	struct page_counter *fail;
   721  	int ret;
   722  
   723  	*ret_pool = NULL;
   724  	if (ret_limit_pool)
   725  		*ret_limit_pool = NULL;
   726  
   727  	/*
   728  	 * hold on to css, as cgroup can be removed but resource
   729  	 * accounting happens on css.
   730  	 */
   731  	cg = get_current_dmemcs();
   732  
   733  	pool = get_cg_pool_unlocked(cg, region);
   734  	if (IS_ERR(pool)) {
   735  		ret = PTR_ERR(pool);
   736  		goto err;
   737  	}
   738  
   739> 	if (!page_counter_try_charge(&pool->cnt, size, &fail)) {
   740  		if (ret_limit_pool) {
   741  			*ret_limit_pool = container_of(fail, struct dmem_cgroup_pool_state, cnt);
   742  			css_get(&(*ret_limit_pool)->cs->css);
   743  			dmemcg_pool_get(*ret_limit_pool);
   744  		}
   745  		dmemcg_pool_put(pool);
   746  		ret = -EAGAIN;
   747  		goto err;
   748  	}
   749  
   750  	/* On success, reference from get_current_dmemcs is transferred to *ret_pool */
```

## [8] `fs/verity/verify.c:231` 函数 `verify_data_block`
- 原始特征：`A|assign:next_hidx|hidx>>params->log_arity`
- 32 位构建：i386_allmod
```c
   206  			fsverity_err(inode,
   207  				     "FILE CORRUPTED!  Data past EOF is not zeroed");
   208  			return false;
   209  		}
   210  		return true;
   211  	}
   212  
   213  	/*
   214  	 * Starting at the leaf level, ascend the tree saving hash blocks along
   215  	 * the way until we find a hash block that has already been verified, or
   216  	 * until we reach the root.
   217  	 */
   218  	for (level = 0; level < params->num_levels; level++) {
   219  		unsigned long next_hidx;
   220  		unsigned long hblock_idx;
   221  		pgoff_t hpage_idx;
   222  		unsigned int hblock_offset_in_page;
   223  		unsigned int hoffset;
   224  		struct page *hpage;
   225  		const void *haddr;
   226  
   227  		/*
   228  		 * The index of the block in the current level; also the index
   229  		 * of that block's hash within the next level.
   230  		 */
   231> 		next_hidx = hidx >> params->log_arity;
   232  
   233  		/* Index of the hash block in the tree overall */
   234  		hblock_idx = params->level_start[level] + next_hidx;
   235  
   236  		/* Index of the hash page in the tree overall */
   237  		hpage_idx = hblock_idx >> params->log_blocks_per_page;
   238  
   239  		/* Byte offset of the hash block within the page */
   240  		hblock_offset_in_page =
   241  			(hblock_idx << params->log_blocksize) & ~PAGE_MASK;
   242  
```

## [9] `fs/btrfs/inode.c:645` 函数 `__cow_file_range_inline`
- 原始特征：`A|arg:insert_inline_extent#4|size`
- 32 位构建：i386_allmod, rv32_abi, rv32_nommu
```c
   620  	if (!path) {
   621  		ret = -ENOMEM;
   622  		goto out;
   623  	}
   624  
   625  	trans = btrfs_join_transaction(root);
   626  	if (IS_ERR(trans)) {
   627  		ret = PTR_ERR(trans);
   628  		trans = NULL;
   629  		goto out;
   630  	}
   631  	trans->block_rsv = &inode->block_rsv;
   632  
   633  	drop_args.path = path;
   634  	drop_args.start = 0;
   635  	drop_args.end = fs_info->sectorsize;
   636  	drop_args.drop_cache = true;
   637  	drop_args.replace_extent = true;
   638  	drop_args.extent_item_size = btrfs_file_extent_calc_inline_size(data_len);
   639  	ret = btrfs_drop_extents(trans, root, inode, &drop_args);
   640  	if (unlikely(ret)) {
   641  		btrfs_abort_transaction(trans, ret);
   642  		goto out;
   643  	}
   644  
   645> 	ret = insert_inline_extent(trans, path, inode, drop_args.extent_inserted,
   646  				   size, compressed_size, compress_type,
   647  				   compressed_folio, update_i_size);
   648  	if (unlikely(ret && ret != -ENOSPC)) {
   649  		btrfs_abort_transaction(trans, ret);
   650  		goto out;
   651  	} else if (ret == -ENOSPC) {
   652  		ret = 1;
   653  		goto out;
   654  	}
   655  
   656  	btrfs_update_inode_bytes(inode, size, drop_args.bytes_found);
```

## [10] `kernel/sched/cputime.c:841` 函数 `vtime_delta`
- 原始特征：`A|return:return|clock-vtime->starttime`
- 32 位构建：无
```c
   816  
   817  	if (task_cputime(p, &cputime.utime, &cputime.stime))
   818  		cputime.sum_exec_runtime = task_sched_runtime(p);
   819  	cputime_adjust(&cputime, &p->prev_cputime, ut, st);
   820  }
   821  EXPORT_SYMBOL_GPL(task_cputime_adjusted);
   822  
   823  void thread_group_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)
   824  {
   825  	struct task_cputime cputime;
   826  
   827  	thread_group_cputime(p, &cputime);
   828  	cputime_adjust(&cputime, &p->signal->prev_cputime, ut, st);
   829  }
   830  #endif /* !CONFIG_VIRT_CPU_ACCOUNTING_NATIVE */
   831  
   832  #ifdef CONFIG_VIRT_CPU_ACCOUNTING_GEN
   833  static u64 vtime_delta(struct vtime *vtime)
   834  {
   835  	unsigned long long clock;
   836  
   837  	clock = sched_clock();
   838  	if (clock < vtime->starttime)
   839  		return 0;
   840  
   841> 	return clock - vtime->starttime;
   842  }
   843  
   844  static u64 get_vtime_delta(struct vtime *vtime)
   845  {
   846  	u64 delta = vtime_delta(vtime);
   847  	u64 other;
   848  
   849  	/*
   850  	 * Unlike tick based timing, vtime based timing never has lost
   851  	 * ticks, and no need for steal time accounting to make up for
   852  	 * lost ticks. Vtime accounts a rounded version of actual
```

## [11] `fs/proc/vmcore.c:945` 函数 `update_note_header_size_elf32`
- 原始特征：`A|arg:kmalloc#0|max_sz ; A|arg:elfcorehdr_read_notes#1|max_sz`
- 32 位构建：i386_allmod
```c
   920  }
   921  
   922  /**
   923   * update_note_header_size_elf32 - update p_memsz member of each PT_NOTE entry
   924   *
   925   * @ehdr_ptr: ELF header
   926   *
   927   * This function updates p_memsz member of each PT_NOTE entry in the
   928   * program header table pointed to by @ehdr_ptr to real size of ELF
   929   * note segment.
   930   */
   931  static int __init update_note_header_size_elf32(const Elf32_Ehdr *ehdr_ptr)
   932  {
   933  	int i, rc=0;
   934  	Elf32_Phdr *phdr_ptr;
   935  	Elf32_Nhdr *nhdr_ptr;
   936  
   937  	phdr_ptr = (Elf32_Phdr *)(ehdr_ptr + 1);
   938  	for (i = 0; i < ehdr_ptr->e_phnum; i++, phdr_ptr++) {
   939  		void *notes_section;
   940  		u64 offset, max_sz, sz, real_sz = 0;
   941  		if (phdr_ptr->p_type != PT_NOTE)
   942  			continue;
   943  		max_sz = phdr_ptr->p_memsz;
   944  		offset = phdr_ptr->p_offset;
   945> 		notes_section = kmalloc(max_sz, GFP_KERNEL);
   946  		if (!notes_section)
   947  			return -ENOMEM;
   948  		rc = elfcorehdr_read_notes(notes_section, max_sz, &offset);
   949  		if (rc < 0) {
   950  			kfree(notes_section);
   951  			return rc;
   952  		}
   953  		nhdr_ptr = notes_section;
   954  		while (nhdr_ptr->n_namesz != 0) {
   955  			sz = sizeof(Elf32_Nhdr) +
   956  				(((u64)nhdr_ptr->n_namesz + 3) & ~3) +
```

## [12] `fs/nilfs2/alloc.c:97` 函数 `nilfs_palloc_group`
- 原始特征：`A|return:return|group`
- 32 位构建：i386_allmod
```c
    72  	mi->mi_blocks_per_desc_block =
    73  		nilfs_palloc_groups_per_desc_block(inode) *
    74  		mi->mi_blocks_per_group + 1;
    75  		/*
    76  		 * Number of blocks per descriptor including the
    77  		 * descriptor block
    78  		 */
    79  	return 0;
    80  }
    81  
    82  /**
    83   * nilfs_palloc_group - get group number and offset from an entry number
    84   * @inode: inode of metadata file using this allocator
    85   * @nr: serial number of the entry (e.g. inode number)
    86   * @offset: pointer to store offset number in the group
    87   *
    88   * Return: Number of the group that contains the entry with the index
    89   * specified by @nr.
    90   */
    91  static unsigned long nilfs_palloc_group(const struct inode *inode, __u64 nr,
    92  					unsigned long *offset)
    93  {
    94  	__u64 group = nr;
    95  
    96  	*offset = do_div(group, nilfs_palloc_entries_per_group(inode));
    97> 	return group;
    98  }
    99  
   100  /**
   101   * nilfs_palloc_desc_blkoff - get block offset of a group descriptor block
   102   * @inode: inode of metadata file using this allocator
   103   * @group: group number
   104   *
   105   * Return: Index number in the metadata file of the descriptor block of
   106   * the group specified by @group.
   107   */
   108  static unsigned long
```

## [13] `fs/nilfs2/the_nilfs.c:524` 函数 `nilfs_store_disk_layout`
- 原始特征：`A|arg:nilfs_set_nsegments#1|nsegments`
- 32 位构建：i386_allmod
```c
   499  		nilfs_err(nilfs->ns_sb,
   500  			  "segment count %llu exceeds upper limit (%llu segments)",
   501  			  (unsigned long long)nsegments,
   502  			  (unsigned long long)nilfs_max_segment_count(nilfs));
   503  		return -EINVAL;
   504  	}
   505  
   506  	nblocks = sb_bdev_nr_blocks(nilfs->ns_sb);
   507  	if (nblocks) {
   508  		u64 min_block_count = nsegments * nilfs->ns_blocks_per_segment;
   509  		/*
   510  		 * To avoid failing to mount early device images without a
   511  		 * second superblock, exclude that block count from the
   512  		 * "min_block_count" calculation.
   513  		 */
   514  
   515  		if (nblocks < min_block_count) {
   516  			nilfs_err(nilfs->ns_sb,
   517  				  "total number of segment blocks %llu exceeds device size (%llu blocks)",
   518  				  (unsigned long long)min_block_count,
   519  				  (unsigned long long)nblocks);
   520  			return -EINVAL;
   521  		}
   522  	}
   523  
   524> 	nilfs_set_nsegments(nilfs, nsegments);
   525  	nilfs->ns_crc_seed = le32_to_cpu(sbp->s_crc_seed);
   526  	return 0;
   527  }
   528  
   529  static int nilfs_valid_sb(struct nilfs_super_block *sbp)
   530  {
   531  	static unsigned char sum[4];
   532  	const int sumoff = offsetof(struct nilfs_super_block, s_sum);
   533  	size_t bytes;
   534  	u32 crc;
   535  
```

## [14] `fs/btrfs/reflink.c:66` 函数 `copy_inline_to_page`
- 原始特征：`A|assign:inline_size|size-btrfs_file_extent_calc_inline_size(0) ; A|arg:memcpy_to_folio#3|datal ; A|arg:btrfs_decompress#5|datal ; A|arg:folio_zero_range#1|datal`
- 32 位构建：i386_allmod, rv32_abi, rv32_nommu
```c
    41  		endoff = destoff + olen;
    42  	if (endoff > vfs_inode->i_size) {
    43  		i_size_write(vfs_inode, endoff);
    44  		btrfs_inode_safe_disk_i_size_write(inode, 0);
    45  	}
    46  
    47  	ret = btrfs_update_inode(trans, inode);
    48  	if (unlikely(ret)) {
    49  		btrfs_abort_transaction(trans, ret);
    50  		btrfs_end_transaction(trans);
    51  		return ret;
    52  	}
    53  	return btrfs_end_transaction(trans);
    54  }
    55  
    56  static int copy_inline_to_page(struct btrfs_inode *inode,
    57  			       const u64 file_offset,
    58  			       char *inline_data,
    59  			       const u64 size,
    60  			       const u64 datal,
    61  			       const u8 comp_type)
    62  {
    63  	struct btrfs_fs_info *fs_info = inode->root->fs_info;
    64  	const u32 block_size = fs_info->sectorsize;
    65  	const u64 range_end = file_offset + block_size - 1;
    66> 	const size_t inline_size = size - btrfs_file_extent_calc_inline_size(0);
    67  	char *data_start = inline_data + btrfs_file_extent_calc_inline_size(0);
    68  	struct extent_changeset *data_reserved = NULL;
    69  	struct folio *folio = NULL;
    70  	struct address_space *mapping = inode->vfs_inode.i_mapping;
    71  	int ret;
    72  
    73  	ASSERT(IS_ALIGNED(file_offset, block_size), "file_offset=%llu block_size=%u",
    74  	       file_offset, block_size);
    75  
    76  	/*
    77  	 * We have flushed and locked the ranges of the source and destination
```

## [15] `kernel/bpf/arraymap.c:182` 函数 `array_map_get_hash`
- 原始特征：`A|arg:sha256#1|(u64)array->elem_size*array->map.max_entries`
- 32 位构建：i386_allmod, rv32_abi, rv32_nommu
```c
   157  
   158  	return &array->map;
   159  }
   160  
   161  static void *array_map_elem_ptr(struct bpf_array* array, u32 index)
   162  {
   163  	return array->value + (u64)array->elem_size * index;
   164  }
   165  
   166  /* Called from syscall or from eBPF program */
   167  static void *array_map_lookup_elem(struct bpf_map *map, void *key)
   168  {
   169  	struct bpf_array *array = container_of(map, struct bpf_array, map);
   170  	u32 index = *(u32 *)key;
   171  
   172  	if (unlikely(index >= array->map.max_entries))
   173  		return NULL;
   174  
   175  	return array->value + (u64)array->elem_size * (index & array->index_mask);
   176  }
   177  
   178  static int array_map_get_hash(struct bpf_map *map)
   179  {
   180  	struct bpf_array *array = container_of(map, struct bpf_array, map);
   181  
   182> 	sha256(array->value, (u64)array->elem_size * array->map.max_entries,
   183  	       array->map.sha);
   184  	return 0;
   185  }
   186  
   187  static int array_map_direct_value_addr(const struct bpf_map *map, u64 *imm,
   188  				       u32 off)
   189  {
   190  	struct bpf_array *array = container_of(map, struct bpf_array, map);
   191  
   192  	if (map->max_entries != 1)
   193  		return -ENOTSUPP;
```

## [16] `fs/nfs/direct.c:204` 函数 `nfs_dreq_bytes_left`
- 原始特征：`A|return:return|dreq->max_count-start`
- 32 位构建：i386, i386_allmod, rv32_abi, rv32_nommu
```c
   179  	spin_lock_init(&dreq->lock);
   180  
   181  	return dreq;
   182  }
   183  
   184  static void nfs_direct_req_free(struct kref *kref)
   185  {
   186  	struct nfs_direct_req *dreq = container_of(kref, struct nfs_direct_req, kref);
   187  
   188  	pnfs_release_ds_info(&dreq->ds_cinfo, dreq->inode);
   189  	if (dreq->l_ctx != NULL)
   190  		nfs_put_lock_context(dreq->l_ctx);
   191  	if (dreq->ctx != NULL)
   192  		put_nfs_open_context(dreq->ctx);
   193  	kmem_cache_free(nfs_direct_cachep, dreq);
   194  }
   195  
   196  static void nfs_direct_req_release(struct nfs_direct_req *dreq)
   197  {
   198  	kref_put(&dreq->kref, nfs_direct_req_free);
   199  }
   200  
   201  ssize_t nfs_dreq_bytes_left(struct nfs_direct_req *dreq, loff_t offset)
   202  {
   203  	loff_t start = offset - dreq->io_start;
   204> 	return dreq->max_count - start;
   205  }
   206  EXPORT_SYMBOL_GPL(nfs_dreq_bytes_left);
   207  
   208  /*
   209   * Collects and returns the final error value/byte-count.
   210   */
   211  static ssize_t nfs_direct_wait(struct nfs_direct_req *dreq)
   212  {
   213  	ssize_t result = -EIOCBQUEUED;
   214  
   215  	/* Async requests don't wait here */
```

## [17] `fs/netfs/direct_read.c:190` 函数 `netfs_unbuffered_read_iter_locked`
- 原始特征：`A|arg:netfs_extract_user_iter#1|rreq->len`
- 32 位构建：i386, i386_allmod, rv32_abi, rv32_nommu
```c
   165  	ret = kiocb_write_and_wait(iocb, orig_count);
   166  	if (ret < 0)
   167  		return ret;
   168  	file_accessed(iocb->ki_filp);
   169  
   170  	rreq = netfs_alloc_request(iocb->ki_filp->f_mapping, iocb->ki_filp,
   171  				   iocb->ki_pos, orig_count,
   172  				   iocb->ki_flags & IOCB_DIRECT ?
   173  				   NETFS_DIO_READ : NETFS_UNBUFFERED_READ);
   174  	if (IS_ERR(rreq))
   175  		return PTR_ERR(rreq);
   176  
   177  	netfs_stat(&netfs_n_rh_dio_read);
   178  	trace_netfs_read(rreq, rreq->start, rreq->len, netfs_read_trace_dio_read);
   179  
   180  	/* If this is an async op, we have to keep track of the destination
   181  	 * buffer for ourselves as the caller's iterator will be trashed when
   182  	 * we return.
   183  	 *
   184  	 * In such a case, extract an iterator to represent as much of the the
   185  	 * output buffer as we can manage.  Note that the extraction might not
   186  	 * be able to allocate a sufficiently large bvec array and may shorten
   187  	 * the request.
   188  	 */
   189  	if (user_backed_iter(iter)) {
   190> 		ret = netfs_extract_user_iter(iter, rreq->len, &rreq->buffer.iter, 0);
   191  		if (ret < 0)
   192  			goto error_put;
   193  		rreq->direct_bv = (struct bio_vec *)rreq->buffer.iter.bvec;
   194  		rreq->direct_bv_count = ret;
   195  		rreq->direct_bv_unpin = iov_iter_extract_will_pin(iter);
   196  		rreq->len = iov_iter_count(&rreq->buffer.iter);
   197  	} else {
   198  		rreq->buffer.iter = *iter;
   199  		rreq->len = orig_count;
   200  		rreq->direct_bv_unpin = false;
   201  		iov_iter_advance(iter, orig_count);
```

## [18] `kernel/bpf/helpers.c:4238` 函数 `bpf_lookup_user_key`
- 原始特征：`A|arg:lookup_user_key#1|flags`
- 32 位构建：i386_allmod, rv32_abi, rv32_nommu
```c
  4213   *
  4214   * Permission checks are deferred to the time the key is used by
  4215   * one of the available key-specific kfuncs.
  4216   *
  4217   * Set *flags* with KEY_LOOKUP_CREATE, to attempt creating a requested
  4218   * special keyring (e.g. session keyring), if it doesn't yet exist.
  4219   * Set *flags* with KEY_LOOKUP_PARTIAL, to lookup a key without waiting
  4220   * for the key construction, and to retrieve uninstantiated keys (keys
  4221   * without data attached to them).
  4222   *
  4223   * Return: a bpf_key pointer with a valid key pointer if the key is found, a
  4224   *         NULL pointer otherwise.
  4225   */
  4226  __bpf_kfunc struct bpf_key *bpf_lookup_user_key(s32 serial, u64 flags)
  4227  {
  4228  	key_ref_t key_ref;
  4229  	struct bpf_key *bkey;
  4230  
  4231  	if (flags & ~KEY_LOOKUP_ALL)
  4232  		return NULL;
  4233  
  4234  	/*
  4235  	 * Permission check is deferred until the key is used, as the
  4236  	 * intent of the caller is unknown here.
  4237  	 */
  4238> 	key_ref = lookup_user_key(serial, flags, KEY_DEFER_PERM_CHECK);
  4239  	if (IS_ERR(key_ref))
  4240  		return NULL;
  4241  
  4242  	bkey = kmalloc_obj(*bkey);
  4243  	if (!bkey) {
  4244  		key_put(key_ref_to_ptr(key_ref));
  4245  		return NULL;
  4246  	}
  4247  
  4248  	bkey->key = key_ref_to_ptr(key_ref);
  4249  	bkey->has_ref = true;
```

## [19] `kernel/power/main.c:91` 函数 `ksys_sync_helper`
- 原始特征：`A|assign:elapsed_msecs|ktime_to_ms(ktime_sub(ktime_get(),start))`
- 32 位构建：i386, i386_allmod, rv32_abi, rv32_nommu
```c
    66  
    67  unsigned int lock_system_sleep(void)
    68  {
    69  	unsigned int flags = current->flags;
    70  	current->flags |= PF_NOFREEZE;
    71  	mutex_lock(&system_transition_mutex);
    72  	return flags;
    73  }
    74  EXPORT_SYMBOL_GPL(lock_system_sleep);
    75  
    76  void unlock_system_sleep(unsigned int flags)
    77  {
    78  	if (!(flags & PF_NOFREEZE))
    79  		current->flags &= ~PF_NOFREEZE;
    80  	mutex_unlock(&system_transition_mutex);
    81  }
    82  EXPORT_SYMBOL_GPL(unlock_system_sleep);
    83  
    84  void ksys_sync_helper(void)
    85  {
    86  	ktime_t start;
    87  	long elapsed_msecs;
    88  
    89  	start = ktime_get();
    90  	ksys_sync();
    91> 	elapsed_msecs = ktime_to_ms(ktime_sub(ktime_get(), start));
    92  	pr_info("Filesystems sync: %ld.%03ld seconds\n",
    93  		elapsed_msecs / MSEC_PER_SEC, elapsed_msecs % MSEC_PER_SEC);
    94  }
    95  EXPORT_SYMBOL_GPL(ksys_sync_helper);
    96  
    97  #if defined(CONFIG_SUSPEND) || defined(CONFIG_HIBERNATION)
    98  /* Wakeup events handling resolution while syncing file systems in jiffies */
    99  #define PM_FS_SYNC_WAKEUP_RESOLUTION	5
   100  
   101  static atomic_t pm_fs_sync_count = ATOMIC_INIT(0);
   102  static struct workqueue_struct *pm_fs_sync_wq;
```

## [20] `fs/ocfs2/dlm/dlmdebug.c:290` 函数 `debug_read`
- 原始特征：`A|arg:simple_read_from_buffer#4|i_size_read(file->f_mapping->host)`
- 32 位构建：i386_allmod
```c
   265  		dump_mle(mle, buf, PAGE_SIZE - 1);
   266  		kfree(buf);
   267  	}
   268  }
   269  
   270  #ifdef CONFIG_DEBUG_FS
   271  
   272  static struct dentry *dlm_debugfs_root;
   273  
   274  #define DLM_DEBUGFS_DIR				"o2dlm"
   275  #define DLM_DEBUGFS_DLM_STATE			"dlm_state"
   276  #define DLM_DEBUGFS_LOCKING_STATE		"locking_state"
   277  #define DLM_DEBUGFS_MLE_STATE			"mle_state"
   278  #define DLM_DEBUGFS_PURGE_LIST			"purge_list"
   279  
   280  /* begin - utils funcs */
   281  static int debug_release(struct inode *inode, struct file *file)
   282  {
   283  	kfree(file->private_data);
   284  	return 0;
   285  }
   286  
   287  static ssize_t debug_read(struct file *file, char __user *buf,
   288  			  size_t nbytes, loff_t *ppos)
   289  {
   290> 	return simple_read_from_buffer(buf, nbytes, ppos, file->private_data,
   291  				       i_size_read(file->f_mapping->host));
   292  }
   293  /* end - util funcs */
   294  
   295  /* begin - purge list funcs */
   296  static int debug_purgelist_print(struct dlm_ctxt *dlm, char *buf, int len)
   297  {
   298  	struct dlm_lock_resource *res;
   299  	int out = 0;
   300  	unsigned long total = 0;
   301  
```

## [21] `fs/erofs/zdata.c:1836` 函数 `z_erofs_pcluster_readmore`
- 原始特征：`A|arg:readahead_expand#2|cur-headoffset`
- 32 位构建：i386_allmod
```c
  1811   * Since partial uptodate is still unimplemented for now, we have to use
  1812   * approximate readmore strategies as a start.
  1813   */
  1814  static void z_erofs_pcluster_readmore(struct z_erofs_frontend *f,
  1815  		struct readahead_control *rac, bool backmost)
  1816  {
  1817  	struct inode *inode = f->inode;
  1818  	struct erofs_map_blocks *map = &f->map;
  1819  	erofs_off_t cur, end, headoffset = f->headoffset;
  1820  	int err;
  1821  
  1822  	if (backmost) {
  1823  		if (rac)
  1824  			end = headoffset + readahead_length(rac) - 1;
  1825  		else
  1826  			end = headoffset + PAGE_SIZE - 1;
  1827  		map->m_la = end;
  1828  		err = z_erofs_map_blocks_iter(inode, map,
  1829  					      EROFS_GET_BLOCKS_READMORE);
  1830  		if (err || !(map->m_flags & EROFS_MAP_MAPPED))
  1831  			return;
  1832  
  1833  		/* expand ra for the trailing edge if readahead */
  1834  		if (rac) {
  1835  			cur = round_up(map->m_la + map->m_llen, PAGE_SIZE);
  1836> 			readahead_expand(rac, headoffset, cur - headoffset);
  1837  			return;
  1838  		}
  1839  		end = round_up(end, PAGE_SIZE);
  1840  	} else {
  1841  		end = round_up(map->m_la, PAGE_SIZE);
  1842  		if (!(map->m_flags & EROFS_MAP_MAPPED) || !map->m_llen)
  1843  			return;
  1844  	}
  1845  
  1846  	cur = map->m_la + map->m_llen - 1;
  1847  	while ((cur >= end) && (cur < i_size_read(inode))) {
```

## [22] `fs/afs/yfsclient.c:408` 函数 `yfs_deliver_fs_fetch_data64`
- 原始特征：`A|arg:afs_extract_discard#1|call->remaining`
- 32 位构建：i386_allmod
```c
   383  		_debug("DATA length: %llu", call->remaining);
   384  
   385  		if (call->remaining == 0)
   386  			goto no_more_data;
   387  
   388  		call->iter = &subreq->io_iter;
   389  		call->iov_len = min(call->remaining, subreq->len - subreq->transferred);
   390  		call->unmarshall++;
   391  		fallthrough;
   392  
   393  		/* extract the returned data */
   394  	case 2:
   395  		count_before = call->iov_len;
   396  		_debug("extract data %zu/%llu", count_before, call->remaining);
   397  
   398  		ret = afs_extract_data(call, true);
   399  		subreq->transferred += count_before - call->iov_len;
   400  		if (ret < 0)
   401  			return ret;
   402  
   403  		call->iter = &call->def_iter;
   404  		if (call->remaining)
   405  			goto no_more_data;
   406  
   407  		/* Discard any excess data the server gave us */
   408> 		afs_extract_discard(call, call->remaining);
   409  		call->unmarshall = 3;
   410  		fallthrough;
   411  
   412  	case 3:
   413  		_debug("extract discard %zu/%llu",
   414  		       iov_iter_count(call->iter), call->remaining);
   415  
   416  		ret = afs_extract_data(call, true);
   417  		if (ret < 0)
   418  			return ret;
   419  
```

## [23] `kernel/cgroup/dmem.c:172` 函数 `set_resource_low`
- 原始特征：`A|arg:page_counter_set_low#1|val`
- 32 位构建：i386_allmod
```c
   147  static void dmemcg_pool_free_rcu(struct rcu_head *rcu)
   148  {
   149  	struct dmem_cgroup_pool_state *pool = container_of(rcu, typeof(*pool), rcu);
   150  
   151  	if (pool->parent)
   152  		dmemcg_pool_put(pool->parent);
   153  	kref_put(&pool->region->ref, dmemcg_free_region);
   154  	kfree(pool);
   155  }
   156  
   157  static void free_cg_pool(struct dmem_cgroup_pool_state *pool)
   158  {
   159  	list_del(&pool->region_node);
   160  	dmemcg_pool_put(pool);
   161  }
   162  
   163  static void
   164  set_resource_min(struct dmem_cgroup_pool_state *pool, u64 val, bool nonblock)
   165  {
   166  	page_counter_set_min(&pool->cnt, val);
   167  }
   168  
   169  static void
   170  set_resource_low(struct dmem_cgroup_pool_state *pool, u64 val, bool nonblock)
   171  {
   172> 	page_counter_set_low(&pool->cnt, val);
   173  }
   174  
   175  static void
   176  set_resource_max(struct dmem_cgroup_pool_state *pool, u64 val, bool nonblock)
   177  {
   178  	struct dmem_cgroup_region *region = pool->region;
   179  	unsigned long limit = (unsigned long)val;
   180  
   181  	/* Apply the new limit immediately so concurrent allocations are throttled. */
   182  	xchg(&pool->cnt.max, limit);
   183  
```

## [24] `fs/zonefs/super.c:647` 函数 `zonefs_get_file_inode`
- 原始特征：`A|assign:ino|z->z_sector>>sbi->s_zone_sectors_shift`
- 32 位构建：i386_allmod
```c
   622  	}
   623  
   624  	return fno;
   625  }
   626  
   627  static struct inode *zonefs_get_file_inode(struct inode *dir,
   628  					   struct dentry *dentry)
   629  {
   630  	struct zonefs_zone_group *zgroup = dir->i_private;
   631  	struct super_block *sb = dir->i_sb;
   632  	struct zonefs_sb_info *sbi = ZONEFS_SB(sb);
   633  	struct zonefs_zone *z;
   634  	struct inode *inode;
   635  	ino_t ino;
   636  	long fno;
   637  
   638  	/* Get the file number from the file name */
   639  	fno = zonefs_fname_to_fno(&dentry->d_name);
   640  	if (fno < 0)
   641  		return ERR_PTR(fno);
   642  
   643  	if (!zgroup->g_nr_zones || fno >= zgroup->g_nr_zones)
   644  		return ERR_PTR(-ENOENT);
   645  
   646  	z = &zgroup->g_zones[fno];
   647> 	ino = z->z_sector >> sbi->s_zone_sectors_shift;
   648  	inode = iget_locked(sb, ino);
   649  	if (!inode)
   650  		return ERR_PTR(-ENOMEM);
   651  	if (!(inode_state_read_once(inode) & I_NEW)) {
   652  		WARN_ON_ONCE(inode->i_private != z);
   653  		return inode;
   654  	}
   655  
   656  	inode->i_ino = ino;
   657  	inode->i_mode = z->z_mode;
   658  	inode_set_mtime_to_ts(inode,
```
