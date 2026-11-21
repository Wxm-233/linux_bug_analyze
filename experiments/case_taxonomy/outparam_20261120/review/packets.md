# outparam 审查材料（隐去来源、已打乱）

每条：被调接口、参数和字段、调用方读点、两个构建绑定到的实现及其写入状态、明确未写路径。
判断：完整线索 / 不完整 / 排除 / 未知。完整线索须能指出公共成功条件、两个实际实现、同一对象的读写、可同时成立的分支条件、无初始化或后备写入的依据，并写出一种能推翻判断的具体观察。

## [1] `bdi_collect_stats` 第 1 个参数（`& stats`），字段 `nr_written`
- 调用方：`mm/backing-dev.c:122`（函数 `bdi_debug_stats_show`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 2 个
- riscv：`mm/backing-dev.c:89`，返回类型 void，字段状态 **明确未写**
- x86_64：`mm/backing-dev.c:105`，返回类型 void，字段状态 **未知**
- 明确未写路径（riscv）：返回于 `['mm/backing-dev.c', 101]`，最近条件 []

调用方：
```c
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
```
riscv 的实现：
```c
    85  
    86  #ifdef CONFIG_CGROUP_WRITEBACK
    87  static void bdi_collect_stats(struct backing_dev_info *bdi,
    88  			      struct wb_stats *stats)
    89  {
    90  	struct bdi_writeback *wb;
    91  
    92  	rcu_read_lock();
    93  	list_for_each_entry_rcu(wb, &bdi->wb_list, bdi_node) {
    94  		if (!wb_tryget(wb))
    95  			continue;
    96  
    97  		collect_wb_stats(stats, wb);
    98  		wb_put(wb);
    99  	}
   100  	rcu_read_unlock();
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
```
x86_64 的实现：
```c
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
   136  		   "b_more_io:          %10lu\n"
   137  		   "b_dirty_time:       %10lu\n"
   138  		   "bdi_list:           %10u\n"
   139  		   "state:              %10lx\n",
   140  		   K(stats.nr_writeback),
   141  		   K(stats.nr_reclaimable),
   142  		   K(stats.wb_thresh),
   143  		   K(dirty_thresh),
   144  		   K(background_thresh),
   145  		   K(stats.nr_dirtied),
   146  		   K(stats.nr_written),
```

## [2] `bdi_collect_stats` 第 1 个参数（`& stats`），字段 `nr_reclaimable`
- 调用方：`mm/backing-dev.c:122`（函数 `bdi_debug_stats_show`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 2 个
- riscv：`mm/backing-dev.c:89`，返回类型 void，字段状态 **明确未写**
- x86_64：`mm/backing-dev.c:105`，返回类型 void，字段状态 **未知**
- 明确未写路径（riscv）：返回于 `['mm/backing-dev.c', 101]`，最近条件 []

调用方：
```c
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
```
riscv 的实现：
```c
    85  
    86  #ifdef CONFIG_CGROUP_WRITEBACK
    87  static void bdi_collect_stats(struct backing_dev_info *bdi,
    88  			      struct wb_stats *stats)
    89  {
    90  	struct bdi_writeback *wb;
    91  
    92  	rcu_read_lock();
    93  	list_for_each_entry_rcu(wb, &bdi->wb_list, bdi_node) {
    94  		if (!wb_tryget(wb))
    95  			continue;
    96  
    97  		collect_wb_stats(stats, wb);
    98  		wb_put(wb);
    99  	}
   100  	rcu_read_unlock();
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
```
x86_64 的实现：
```c
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
   136  		   "b_more_io:          %10lu\n"
   137  		   "b_dirty_time:       %10lu\n"
   138  		   "bdi_list:           %10u\n"
   139  		   "state:              %10lx\n",
   140  		   K(stats.nr_writeback),
   141  		   K(stats.nr_reclaimable),
   142  		   K(stats.wb_thresh),
   143  		   K(dirty_thresh),
   144  		   K(background_thresh),
   145  		   K(stats.nr_dirtied),
   146  		   K(stats.nr_written),
```

## [3] `bdi_collect_stats` 第 1 个参数（`& stats`），字段 `nr_io`
- 调用方：`mm/backing-dev.c:122`（函数 `bdi_debug_stats_show`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 2 个
- riscv：`mm/backing-dev.c:89`，返回类型 void，字段状态 **明确未写**
- x86_64：`mm/backing-dev.c:105`，返回类型 void，字段状态 **未知**
- 明确未写路径（riscv）：返回于 `['mm/backing-dev.c', 101]`，最近条件 []

调用方：
```c
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
```
riscv 的实现：
```c
    85  
    86  #ifdef CONFIG_CGROUP_WRITEBACK
    87  static void bdi_collect_stats(struct backing_dev_info *bdi,
    88  			      struct wb_stats *stats)
    89  {
    90  	struct bdi_writeback *wb;
    91  
    92  	rcu_read_lock();
    93  	list_for_each_entry_rcu(wb, &bdi->wb_list, bdi_node) {
    94  		if (!wb_tryget(wb))
    95  			continue;
    96  
    97  		collect_wb_stats(stats, wb);
    98  		wb_put(wb);
    99  	}
   100  	rcu_read_unlock();
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
```
x86_64 的实现：
```c
   101  }
   102  #else
   103  static void bdi_collect_stats(struct backing_dev_info *bdi,
   104  			      struct wb_stats *stats)
   105  {
   106  	collect_wb_stats(stats, &bdi->wb);
   107  }
   108  #endif
   109  
   110  static int bdi_debug_stats_show(struct seq_file *m, void *v)
   111  {
   112  	struct backing_dev_info *bdi = m->private;
   113  	unsigned long background_thresh;
   114  	unsigned long dirty_thresh;
   115  	struct wb_stats stats;
   116  	unsigned long tot_bw;
   117  
   118  	global_dirty_limits(&background_thresh, &dirty_thresh);
   119  
   120  	memset(&stats, 0, sizeof(stats));
   121  	stats.dirty_thresh = dirty_thresh;
   122  	bdi_collect_stats(bdi, &stats);
   123  	tot_bw = atomic_long_read(&bdi->tot_write_bandwidth);
   124  
   125  	seq_printf(m,
   126  		   "BdiWriteback:       %10lu kB\n"
   127  		   "BdiReclaimable:     %10lu kB\n"
   128  		   "BdiDirtyThresh:     %10lu kB\n"
   129  		   "DirtyThresh:        %10lu kB\n"
   130  		   "BackgroundThresh:   %10lu kB\n"
   131  		   "BdiDirtied:         %10lu kB\n"
   132  		   "BdiWritten:         %10lu kB\n"
   133  		   "BdiWriteBandwidth:  %10lu kBps\n"
   134  		   "b_dirty:            %10lu\n"
   135  		   "b_io:               %10lu\n"
   136  		   "b_more_io:          %10lu\n"
   137  		   "b_dirty_time:       %10lu\n"
   138  		   "bdi_list:           %10u\n"
   139  		   "state:              %10lx\n",
   140  		   K(stats.nr_writeback),
   141  		   K(stats.nr_reclaimable),
   142  		   K(stats.wb_thresh),
   143  		   K(dirty_thresh),
   144  		   K(background_thresh),
   145  		   K(stats.nr_dirtied),
   146  		   K(stats.nr_written),
```

## [4] `wbc_attach_fdatawrite_inode` 第 0 个参数（`& wbc`），字段 `nr_to_write`
- 调用方：`mm/filemap.c:386`（函数 `filemap_writeback`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 2 个
- riscv：`fs/fs-writeback.c:860`，返回类型 void，字段状态 **未知**
- x86_64：`include/linux/writeback.h:282`，返回类型 void，字段状态 **明确未写**
- 明确未写路径（x86_64）：返回于 `['include/linux/writeback.h', 283]`，最近条件 []

调用方：
```c
   374  	struct writeback_control wbc = {
   375  		.sync_mode	= sync_mode,
   376  		.nr_to_write	= nr_to_write ? *nr_to_write : LONG_MAX,
   377  		.range_start	= start,
   378  		.range_end	= end,
   379  	};
   380  	int ret;
   381  
   382  	if (!mapping_can_writeback(mapping) ||
   383  	    !mapping_tagged(mapping, PAGECACHE_TAG_DIRTY))
   384  		return 0;
   385  
   386  	wbc_attach_fdatawrite_inode(&wbc, mapping->host);
   387  	ret = do_writepages(mapping, &wbc);
   388  	wbc_detach_inode(&wbc);
   389  
   390  	if (!ret && nr_to_write)
   391  		*nr_to_write = wbc.nr_to_write;
   392  	return ret;
   393  }
   394  
   395  /**
   396   * filemap_fdatawrite_range - start writeback on mapping dirty pages in range
   397   * @mapping:	address space structure to write
   398   * @start:	offset in bytes where the range starts
   399   * @end:	offset in bytes where the range ends (inclusive)
```
riscv 的实现：
```c
   848  
   849  /**
   850   * wbc_attach_fdatawrite_inode - associate wbc and inode for fdatawrite
   851   * @wbc: writeback_control of interest
   852   * @inode: target inode
   853   *
   854   * This function is to be used by filemap_writeback(), which is an alternative
   855   * entry point into writeback code, and first ensures @inode is associated with
   856   * a bdi_writeback and attaches it to @wbc.
   857   */
   858  void wbc_attach_fdatawrite_inode(struct writeback_control *wbc,
   859  		struct inode *inode)
   860  {
   861  	spin_lock(&inode->i_lock);
   862  	inode_attach_wb(inode, NULL);
   863  	wbc_attach_and_unlock_inode(wbc, inode);
   864  }
   865  EXPORT_SYMBOL_GPL(wbc_attach_fdatawrite_inode);
   866  
   867  /**
   868   * wbc_detach_inode - disassociate wbc from inode and perform foreign detection
   869   * @wbc: writeback_control of the just finished writeback
   870   *
   871   * To be called after a writeback attempt of an inode finishes and undoes
   872   * wbc_attach_and_unlock_inode().  Can be called under any context.
   873   *
   874   * As concurrent write sharing of an inode is expected to be very rare and
   875   * memcg only tracks page ownership on first-use basis severely confining
   876   * the usefulness of such sharing, cgroup writeback tracks ownership
   877   * per-inode.  While the support for concurrent write sharing of an inode
   878   * is deemed unnecessary, an inode being written to by different cgroups at
   879   * different points in time is a lot more common, and, more importantly,
   880   * charging only by first-use can too readily lead to grossly incorrect
   881   * behaviors (single foreign page can lead to gigabytes of writeback to be
   882   * incorrectly attributed).
   883   *
   884   * To resolve this issue, cgroup writeback detects the majority dirtier of
   885   * an inode and transfers the ownership to it.  To avoid unnecessary
   886   * oscillation, the detection mechanism keeps track of history and gives
   887   * out the switch verdict only if the foreign usage pattern is stable over
   888   * a certain amount of time and/or writeback attempts.
   889   *
   890   * On each writeback attempt, @wbc tries to detect the majority writer
   891   * using Boyer-Moore majority vote algorithm.  In addition to the byte
   892   * count from the majority voting, it also counts the bytes written for the
   893   * current wb and the last round's winner wb (max of last round's current
```
x86_64 的实现：
```c
   279  
   280  static inline void wbc_attach_fdatawrite_inode(struct writeback_control *wbc,
   281  					       struct inode *inode)
   282  {
   283  }
   284  
   285  static inline void wbc_detach_inode(struct writeback_control *wbc)
   286  {
   287  }
   288  
   289  static inline void wbc_init_bio(struct writeback_control *wbc, struct bio *bio)
   290  {
   291  }
   292  
   293  static inline void wbc_account_cgroup_owner(struct writeback_control *wbc,
   294  					    struct folio *folio, size_t bytes)
   295  {
   296  }
   297  
   298  static inline void cgroup_writeback_umount(struct super_block *sb)
   299  {
   300  }
   301  
   302  #endif	/* CONFIG_CGROUP_WRITEBACK */
   303  
   304  /*
   305   * mm/page-writeback.c
   306   */
   307  /* consolidated parameters for balance_dirty_pages() and its subroutines */
   308  struct dirty_throttle_control {
   309  #ifdef CONFIG_CGROUP_WRITEBACK
   310  	struct wb_domain	*dom;
   311  	struct dirty_throttle_control *gdtc;	/* only set in memcg dtc's */
   312  #endif
   313  	struct bdi_writeback	*wb;
   314  	struct fprop_local_percpu *wb_completions;
   315  
   316  	unsigned long		avail;		/* dirtyable */
   317  	unsigned long		dirty;		/* file_dirty + write + nfs */
   318  	unsigned long		thresh;		/* dirty threshold */
   319  	unsigned long		bg_thresh;	/* dirty background threshold */
   320  	unsigned long		limit;		/* hard dirty limit */
   321  
   322  	unsigned long		wb_dirty;	/* per-wb counterparts */
   323  	unsigned long		wb_thresh;
   324  	unsigned long		wb_bg_thresh;
```

## [5] `alloc_cpumask_var` 第 0 个参数（`& full_hk_cpus`），字段 `*`
- 调用方：`kernel/cgroup/cpuset.c:1383`（函数 `isolated_cpus_can_update`）；检查了返回值：True；调用前初始化：无；成功分支上干净读：True；同类见证点 22 个
- riscv：`include/linux/cpumask.h:1078`，返回类型 bool，字段状态 **明确未写**
- arm64：`include/linux/cpumask.h:1052`，返回类型 bool，字段状态 **未知**
- 明确未写路径（riscv）：返回于 `['include/linux/cpumask.h', 1079]`，最近条件 []

调用方：
```c
  1371  				     struct cpumask *del_cpus)
  1372  {
  1373  	cpumask_var_t full_hk_cpus;
  1374  	int res = true;
  1375  
  1376  	if (!housekeeping_enabled(HK_TYPE_KERNEL_NOISE))
  1377  		return true;
  1378  
  1379  	if (del_cpus && cpumask_weight_and(del_cpus,
  1380  			housekeeping_cpumask(HK_TYPE_KERNEL_NOISE)))
  1381  		return true;
  1382  
  1383  	if (!alloc_cpumask_var(&full_hk_cpus, GFP_KERNEL))
  1384  		return false;
  1385  
  1386  	cpumask_and(full_hk_cpus, housekeeping_cpumask(HK_TYPE_KERNEL_NOISE),
  1387  		    housekeeping_cpumask(HK_TYPE_DOMAIN));
  1388  	cpumask_andnot(full_hk_cpus, full_hk_cpus, isolated_cpus);
  1389  	cpumask_and(full_hk_cpus, full_hk_cpus, cpu_active_mask);
  1390  	if (!cpumask_weight_andnot(full_hk_cpus, add_cpus))
  1391  		res = false;
  1392  
  1393  	free_cpumask_var(full_hk_cpus);
  1394  	return res;
  1395  }
  1396  
```
riscv 的实现：
```c
  1076  
  1077  static __always_inline bool alloc_cpumask_var(cpumask_var_t *mask, gfp_t flags)
  1078  {
  1079  	return true;
  1080  }
  1081  
  1082  static __always_inline bool alloc_cpumask_var_node(cpumask_var_t *mask, gfp_t flags,
  1083  					  int node)
  1084  {
  1085  	return true;
  1086  }
  1087  
  1088  static __always_inline bool zalloc_cpumask_var(cpumask_var_t *mask, gfp_t flags)
  1089  {
  1090  	cpumask_clear(*mask);
  1091  	return true;
  1092  }
  1093  
  1094  static __always_inline bool zalloc_cpumask_var_node(cpumask_var_t *mask, gfp_t flags,
  1095  					  int node)
  1096  {
  1097  	cpumask_clear(*mask);
  1098  	return true;
  1099  }
  1100  
  1101  static __always_inline void alloc_bootmem_cpumask_var(cpumask_var_t *mask)
  1102  {
  1103  }
  1104  
  1105  static __always_inline void free_cpumask_var(cpumask_var_t mask)
  1106  {
  1107  }
  1108  
  1109  static __always_inline void free_bootmem_cpumask_var(cpumask_var_t mask)
  1110  {
  1111  }
  1112  
  1113  static __always_inline bool cpumask_available(cpumask_var_t mask)
  1114  {
  1115  	return true;
  1116  }
  1117  #endif /* CONFIG_CPUMASK_OFFSTACK */
  1118  
  1119  DEFINE_FREE(free_cpumask_var, struct cpumask *, if (_T) free_cpumask_var(_T));
  1120  
  1121  /* It's common to want to use cpu_all_mask in struct member initializers,
```
arm64 的实现：
```c
  1037  
  1038  /**
  1039   * alloc_cpumask_var - allocate a struct cpumask
  1040   * @mask: pointer to cpumask_var_t where the cpumask is returned
  1041   * @flags: GFP_ flags
  1042   *
  1043   * Only defined when CONFIG_CPUMASK_OFFSTACK=y, otherwise is
  1044   * a nop returning a constant 1 (in <linux/cpumask.h>).
  1045   *
  1046   * See alloc_cpumask_var_node.
  1047   *
  1048   * Return: %true if allocation succeeded, %false if not
  1049   */
  1050  static __always_inline
  1051  bool alloc_cpumask_var(cpumask_var_t *mask, gfp_t flags)
  1052  {
  1053  	return alloc_cpumask_var_node(mask, flags, NUMA_NO_NODE);
  1054  }
  1055  
  1056  static __always_inline
  1057  bool zalloc_cpumask_var(cpumask_var_t *mask, gfp_t flags)
  1058  {
  1059  	return alloc_cpumask_var(mask, flags | __GFP_ZERO);
  1060  }
  1061  
  1062  void alloc_bootmem_cpumask_var(cpumask_var_t *mask);
  1063  void free_cpumask_var(cpumask_var_t mask);
  1064  void free_bootmem_cpumask_var(cpumask_var_t mask);
  1065  
  1066  static __always_inline bool cpumask_available(cpumask_var_t mask)
  1067  {
  1068  	return mask != NULL;
  1069  }
  1070  
  1071  #else
  1072  
  1073  #define this_cpu_cpumask_var_ptr(x) this_cpu_ptr(x)
  1074  #define __cpumask_var_read_mostly
  1075  #define CPUMASK_VAR_NULL {}
  1076  
  1077  static __always_inline bool alloc_cpumask_var(cpumask_var_t *mask, gfp_t flags)
  1078  {
  1079  	return true;
  1080  }
  1081  
  1082  static __always_inline bool alloc_cpumask_var_node(cpumask_var_t *mask, gfp_t flags,
```

## [6] `arch_stack_walk_reliable` 第 1 个参数（`& c`），字段 `len`
- 调用方：`kernel/stacktrace.c:209`（函数 `stack_trace_save_tsk_reliable`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 1 个
- arm64：`arch/arm64/kernel/stacktrace.c:413`，返回类型 other，字段状态 **未知**
- x86_64：`arch/x86/kernel/stacktrace.c:34`，返回类型 other，字段状态 **明确未写**
- 明确未写路径（x86_64）：返回于 `['arch/x86/kernel/stacktrace.c', 47]`，最近条件 ['regs', 'user_mode ( regs )']

调用方：
```c
   197  		.store	= store,
   198  		.size	= size,
   199  	};
   200  	int ret;
   201  
   202  	/*
   203  	 * If the task doesn't have a stack (e.g., a zombie), the stack is
   204  	 * "reliably" empty.
   205  	 */
   206  	if (!try_get_task_stack(tsk))
   207  		return 0;
   208  
   209  	ret = arch_stack_walk_reliable(consume_entry, &c, tsk);
   210  	put_task_stack(tsk);
   211  	return ret ? ret : c.len;
   212  }
   213  #endif
   214  
   215  #ifdef CONFIG_USER_STACKTRACE_SUPPORT
   216  /**
   217   * stack_trace_save_user - Save a user space stack trace into a storage array
   218   * @store:	Pointer to storage array
   219   * @size:	Size of the storage array
   220   *
   221   * Return: Number of trace entries stored.
   222   */
```
arm64 的实现：
```c
   409  
   410  noinline noinstr int arch_stack_walk_reliable(stack_trace_consume_fn consume_entry,
   411  					      void *cookie,
   412  					      struct task_struct *task)
   413  {
   414  	struct kunwind_consume_entry_data data = {
   415  		.consume_entry = consume_entry,
   416  		.cookie = cookie,
   417  	};
   418  
   419  	return kunwind_stack_walk(arch_reliable_kunwind_consume_entry, &data,
   420  				  task, NULL);
   421  }
   422  
   423  struct bpf_unwind_consume_entry_data {
   424  	bool (*consume_entry)(void *cookie, u64 ip, u64 sp, u64 fp);
   425  	void *cookie;
   426  };
   427  
   428  static bool
   429  arch_bpf_unwind_consume_entry(const struct kunwind_state *state, void *cookie)
   430  {
   431  	struct bpf_unwind_consume_entry_data *data = cookie;
   432  
   433  	return data->consume_entry(data->cookie, state->common.pc, 0,
   434  				   state->common.fp);
   435  }
   436  
   437  noinline noinstr void arch_bpf_stack_walk(bool (*consume_entry)(void *cookie, u64 ip, u64 sp,
   438  								u64 fp), void *cookie)
   439  {
   440  	struct bpf_unwind_consume_entry_data data = {
   441  		.consume_entry = consume_entry,
   442  		.cookie = cookie,
   443  	};
   444  
   445  	kunwind_stack_walk(arch_bpf_unwind_consume_entry, &data, current, NULL);
   446  }
   447  
   448  static const char *state_source_string(const struct kunwind_state *state)
   449  {
   450  	switch (state->source) {
   451  	case KUNWIND_SOURCE_FRAME:	return NULL;
   452  	case KUNWIND_SOURCE_CALLER:	return "C";
   453  	case KUNWIND_SOURCE_TASK:	return "T";
   454  	case KUNWIND_SOURCE_REGS_PC:	return "P";
```
x86_64 的实现：
```c
    31  
    32  int arch_stack_walk_reliable(stack_trace_consume_fn consume_entry,
    33  			     void *cookie, struct task_struct *task)
    34  {
    35  	struct unwind_state state;
    36  	struct pt_regs *regs;
    37  	unsigned long addr;
    38  
    39  	for (unwind_start(&state, task, NULL, NULL);
    40  	     !unwind_done(&state) && !unwind_error(&state);
    41  	     unwind_next_frame(&state)) {
    42  
    43  		regs = unwind_get_entry_regs(&state, NULL);
    44  		if (regs) {
    45  			/* Success path for user tasks */
    46  			if (user_mode(regs))
    47  				return 0;
    48  
    49  			/*
    50  			 * Kernel mode registers on the stack indicate an
    51  			 * in-kernel interrupt or exception (e.g., preemption
    52  			 * or a page fault), which can make frame pointers
    53  			 * unreliable.
    54  			 */
    55  			if (IS_ENABLED(CONFIG_FRAME_POINTER))
    56  				return -EINVAL;
    57  		}
    58  
    59  		addr = unwind_get_return_address(&state);
    60  
    61  		/*
    62  		 * A NULL or invalid return address probably means there's some
    63  		 * generated code which __kernel_text_address() doesn't know
    64  		 * about.
    65  		 */
    66  		if (!addr)
    67  			return -EINVAL;
    68  
    69  		if (!consume_entry(cookie, addr))
    70  			return -EINVAL;
    71  	}
    72  
    73  	/* Check for stack corruption */
    74  	if (unwind_error(&state))
    75  		return -EINVAL;
    76  
```

## [7] `huge_node` 第 3 个参数（`& mpol`），字段 `*`
- 调用方：`mm/hugetlb.c:3014`（函数 `alloc_hugetlb_folio`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：True；同类见证点 2 个
- riscv：`include/linux/mempolicy.h:262`，返回类型 other，字段状态 **必写**
- arm64：`mm/mempolicy.c:2323`，返回类型 other，字段状态 **未知**

调用方：
```c
  3002  	 */
  3003  	if (map_chg != MAP_CHG_REUSE)
  3004  		alloc_flags |= HUGETLB_ALLOC_CHARG_CGROUP_RSVD;
  3005  
  3006  	/*
  3007  	 * gbl_chg == 0 indicates a reservation exists for this
  3008  	 * allocation, so try to use it.
  3009  	 */
  3010  	if (gbl_chg == 0)
  3011  		alloc_flags |= HUGETLB_ALLOC_USE_GLOBAL_RESERVATIONS;
  3012  
  3013  	/* Takes reference on mpol. */
  3014  	nid = huge_node(vma, addr, gfp, &mpol, &nodemask);
  3015  	mpoli = (struct mempolicy_interpreted){
  3016  		.nid = nid,
  3017  #ifdef CONFIG_NUMA
  3018  		.mode = mpol ? mpol->mode : MPOL_DEFAULT,
  3019  #else
  3020  		.mode = MPOL_DEFAULT,
  3021  #endif
  3022  		.nodemask = nodemask,
  3023  	};
  3024  
  3025  	folio = hugetlb_alloc_folio(h, &mpoli, alloc_flags);
  3026  
  3027  	mpol_cond_put(mpol);
```
riscv 的实现：
```c
   258  
   259  static inline int huge_node(struct vm_area_struct *vma,
   260  				unsigned long addr, gfp_t gfp_flags,
   261  				struct mempolicy **mpol, nodemask_t **nodemask)
   262  {
   263  	*mpol = NULL;
   264  	*nodemask = NULL;
   265  	return 0;
   266  }
   267  
   268  static inline bool init_nodemask_of_mempolicy(nodemask_t *m)
   269  {
   270  	return false;
   271  }
   272  
   273  static inline int do_migrate_pages(struct mm_struct *mm, const nodemask_t *from,
   274  				   const nodemask_t *to, int flags)
   275  {
   276  	return 0;
   277  }
   278  
   279  static inline void check_highest_zone(int k)
   280  {
   281  }
   282  
   283  #ifdef CONFIG_TMPFS
   284  static inline int mpol_parse_str(char *str, struct mempolicy **mpol)
   285  {
   286  	return 1;	/* error */
   287  }
   288  #endif
   289  
   290  static inline int mpol_misplaced(struct folio *folio,
   291  				 struct vm_fault *vmf,
   292  				 unsigned long address)
   293  {
   294  	return -1; /* no node preference */
   295  }
   296  
   297  static inline void mpol_put_task_policy(struct task_struct *task)
   298  {
   299  }
   300  
   301  static inline bool mpol_is_preferred_many(struct mempolicy *pol)
   302  {
   303  	return  false;
```
arm64 的实现：
```c
  2306  
  2307  #ifdef CONFIG_HUGETLBFS
  2308  /*
  2309   * huge_node(@vma, @addr, @gfp_flags, @mpol)
  2310   * @vma: virtual memory area whose policy is sought
  2311   * @addr: address in @vma for shared policy lookup and interleave policy
  2312   * @gfp_flags: for requested zone
  2313   * @mpol: pointer to mempolicy pointer for reference counted mempolicy
  2314   * @nodemask: pointer to nodemask pointer for 'bind' and 'prefer-many' policy
  2315   *
  2316   * Returns a nid suitable for a huge page allocation and a pointer
  2317   * to the struct mempolicy for conditional unref after allocation.
  2318   * If the effective policy is 'bind' or 'prefer-many', returns a pointer
  2319   * to the mempolicy's @nodemask for filtering the zonelist.
  2320   */
  2321  int huge_node(struct vm_area_struct *vma, unsigned long addr, gfp_t gfp_flags,
  2322  		struct mempolicy **mpol, nodemask_t **nodemask)
  2323  {
  2324  	pgoff_t ilx;
  2325  	int nid;
  2326  
  2327  	nid = numa_node_id();
  2328  	*mpol = get_vma_policy(vma, addr, hstate_vma(vma)->order, &ilx);
  2329  	*nodemask = policy_nodemask(gfp_flags, *mpol, ilx, &nid);
  2330  	return nid;
  2331  }
  2332  
  2333  /*
  2334   * init_nodemask_of_mempolicy
  2335   *
  2336   * If the current task's mempolicy is "default" [NULL], return 'false'
  2337   * to indicate default policy.  Otherwise, extract the policy nodemask
  2338   * for 'bind' or 'interleave' policy into the argument nodemask, or
  2339   * initialize the argument nodemask to contain the single node for
  2340   * 'preferred' or 'local' policy and return 'true' to indicate presence
  2341   * of non-default mempolicy.
  2342   *
  2343   * We don't bother with reference counting the mempolicy [mpol_get/put]
  2344   * because the current task is examining it's own mempolicy and a task's
  2345   * mempolicy is only ever changed by the task itself.
  2346   *
  2347   * N.B., it is the caller's responsibility to free a returned nodemask.
  2348   */
  2349  bool init_nodemask_of_mempolicy(nodemask_t *mask)
  2350  {
  2351  	struct mempolicy *mempolicy;
```

## [8] `mem_cgroup_wb_stats` 第 1 个参数（`& filepages`），字段 `*`
- 调用方：`mm/page-writeback.c:849`（函数 `domain_dirty_avail`）；检查了返回值：False；调用前初始化：无；成功分支上干净读：False；同类见证点 2 个
- riscv：`mm/memcontrol.c:3826`，返回类型 void，字段状态 **必写**
- x86_64：`include/linux/memcontrol.h:1617`，返回类型 void，字段状态 **明确未写**
- 明确未写路径（x86_64）：返回于 `['include/linux/memcontrol.h', 1618]`，最近条件 []

调用方：
```c
   837   */
   838  static void domain_dirty_avail(struct dirty_throttle_control *dtc,
   839  			       bool include_writeback)
   840  {
   841  	if (dtc_is_global(dtc)) {
   842  		dtc->avail = global_dirtyable_memory();
   843  		dtc->dirty = global_node_page_state(NR_FILE_DIRTY);
   844  		if (include_writeback)
   845  			dtc->dirty += global_node_page_state(NR_WRITEBACK);
   846  	} else {
   847  		unsigned long filepages = 0, headroom = 0, writeback = 0;
   848  
   849  		mem_cgroup_wb_stats(dtc->wb, &filepages, &headroom, &dtc->dirty,
   850  				    &writeback);
   851  		if (include_writeback)
   852  			dtc->dirty += writeback;
   853  		mdtc_calc_avail(dtc, filepages, headroom);
   854  	}
   855  }
   856  
   857  /**
   858   * __wb_calc_thresh - @wb's share of dirty threshold
   859   * @dtc: dirty_throttle_context of interest
   860   * @thresh: dirty throttling or dirty background threshold of wb_domain in @dtc
   861   *
   862   * Note that balance_dirty_pages() will only seriously take dirty throttling
```
riscv 的实现：
```c
  3804  
  3805  /**
  3806   * mem_cgroup_wb_stats - retrieve writeback related stats from its memcg
  3807   * @wb: bdi_writeback in question
  3808   * @pfilepages: out parameter for number of file pages
  3809   * @pheadroom: out parameter for number of allocatable pages according to memcg
  3810   * @pdirty: out parameter for number of dirty pages
  3811   * @pwriteback: out parameter for number of pages under writeback
  3812   *
  3813   * Determine the numbers of file, headroom, dirty, and writeback pages in
  3814   * @wb's memcg.  File, dirty and writeback are self-explanatory.  Headroom
  3815   * is a bit more involved.
  3816   *
  3817   * A memcg's headroom is "min(max, high) - used".  In the hierarchy, the
  3818   * headroom is calculated as the lowest headroom of itself and the
  3819   * ancestors.  Note that this doesn't consider the actual amount of
  3820   * available memory in the system.  The caller should further cap
  3821   * *@pheadroom accordingly.
  3822   */
  3823  void mem_cgroup_wb_stats(struct bdi_writeback *wb, unsigned long *pfilepages,
  3824  			 unsigned long *pheadroom, unsigned long *pdirty,
  3825  			 unsigned long *pwriteback)
  3826  {
  3827  	struct mem_cgroup *memcg = mem_cgroup_from_css(wb->memcg_css);
  3828  	struct mem_cgroup *parent;
  3829  
  3830  	mem_cgroup_flush_stats_ratelimited(memcg);
  3831  
  3832  	*pdirty = memcg_page_state(memcg, NR_FILE_DIRTY);
  3833  	*pwriteback = memcg_page_state(memcg, NR_WRITEBACK);
  3834  	*pfilepages = memcg_page_state(memcg, NR_INACTIVE_FILE) +
  3835  			memcg_page_state(memcg, NR_ACTIVE_FILE);
  3836  
  3837  	*pheadroom = PAGE_COUNTER_MAX;
  3838  	while ((parent = parent_mem_cgroup(memcg))) {
  3839  		unsigned long ceiling = min(READ_ONCE(memcg->memory.max),
  3840  					    READ_ONCE(memcg->memory.high));
  3841  		unsigned long used = page_counter_read(&memcg->memory);
  3842  
  3843  		*pheadroom = min(*pheadroom, ceiling - min(ceiling, used));
  3844  		memcg = parent;
  3845  	}
  3846  }
  3847  
  3848  /*
  3849   * Foreign dirty flushing
```
x86_64 的实现：
```c
  1611  
  1612  static inline void mem_cgroup_wb_stats(struct bdi_writeback *wb,
  1613  				       unsigned long *pfilepages,
  1614  				       unsigned long *pheadroom,
  1615  				       unsigned long *pdirty,
  1616  				       unsigned long *pwriteback)
  1617  {
  1618  }
  1619  
  1620  static inline void mem_cgroup_track_foreign_dirty(struct folio *folio,
  1621  						  struct bdi_writeback *wb)
  1622  {
  1623  }
  1624  
  1625  static inline void mem_cgroup_flush_foreign(struct bdi_writeback *wb)
  1626  {
  1627  }
  1628  
  1629  #endif	/* CONFIG_CGROUP_WRITEBACK */
  1630  
  1631  struct sock;
  1632  #ifdef CONFIG_MEMCG
  1633  extern struct static_key_false memcg_sockets_enabled_key;
  1634  #define mem_cgroup_sockets_enabled static_branch_unlikely(&memcg_sockets_enabled_key)
  1635  
  1636  void mem_cgroup_sk_alloc(struct sock *sk);
  1637  void mem_cgroup_sk_free(struct sock *sk);
  1638  void mem_cgroup_sk_inherit(const struct sock *sk, struct sock *newsk);
  1639  bool mem_cgroup_sk_charge(const struct sock *sk, unsigned int nr_pages,
  1640  			  gfp_t gfp_mask);
  1641  void mem_cgroup_sk_uncharge(const struct sock *sk, unsigned int nr_pages);
  1642  
  1643  #if BITS_PER_LONG < 64
  1644  static inline void mem_cgroup_set_socket_pressure(struct mem_cgroup *memcg)
  1645  {
  1646  	u64 val = get_jiffies_64() + HZ;
  1647  	unsigned long flags;
  1648  
  1649  	write_seqlock_irqsave(&memcg->socket_pressure_seqlock, flags);
  1650  	memcg->socket_pressure = val;
  1651  	write_sequnlock_irqrestore(&memcg->socket_pressure_seqlock, flags);
  1652  }
  1653  
  1654  static inline u64 mem_cgroup_get_socket_pressure(struct mem_cgroup *memcg)
  1655  {
  1656  	unsigned int seq;
```

## [9] `arch_futex_atomic_op_inuser` 第 2 个参数（`& oldval`），字段 `*`
- 调用方：`kernel/futex/waitwake.c:251`（函数 `futex_atomic_op_inuser`）；检查了返回值：True；调用前初始化：无；成功分支上干净读：True；同类见证点 2 个
- riscv：`arch/riscv/include/asm/futex.h:38`，返回类型 other，字段状态 **未知**
- x86_64：`arch/x86/include/asm/futex.h:50`，返回类型 other，字段状态 **明确未写**
- 明确未写路径（x86_64）：返回于 `['arch/x86/include/asm/futex.h', 72]`，最近条件 []

调用方：
```c
   239  			/*
   240  			 * kill this print and return -EINVAL when userspace
   241  			 * is sane again
   242  			 */
   243  			pr_info_ratelimited("futex_wake_op: %s tries to shift op by %d; fix this program\n",
   244  					    current->comm, oparg);
   245  			oparg &= 31;
   246  		}
   247  		oparg = 1 << oparg;
   248  	}
   249  
   250  	pagefault_disable();
   251  	ret = arch_futex_atomic_op_inuser(op, oparg, &oldval, uaddr);
   252  	pagefault_enable();
   253  	if (ret)
   254  		return ret;
   255  
   256  	switch (cmp) {
   257  	case FUTEX_OP_CMP_EQ:
   258  		return oldval == cmparg;
   259  	case FUTEX_OP_CMP_NE:
   260  		return oldval != cmparg;
   261  	case FUTEX_OP_CMP_LT:
   262  		return oldval < cmparg;
   263  	case FUTEX_OP_CMP_GE:
   264  		return oldval >= cmparg;
```
riscv 的实现：
```c
    35  
    36  static inline int
    37  arch_futex_atomic_op_inuser(int op, int oparg, int *oval, u32 __user *uaddr)
    38  {
    39  	int oldval = 0, ret = 0;
    40  
    41  	if (!access_ok(uaddr, sizeof(u32)))
    42  		return -EFAULT;
    43  
    44  	switch (op) {
    45  	case FUTEX_OP_SET:
    46  		__futex_atomic_op("amoswap.w.aqrl %[ov],%z[op],%[u]",
    47  				  ret, oldval, uaddr, oparg);
    48  		break;
    49  	case FUTEX_OP_ADD:
    50  		__futex_atomic_op("amoadd.w.aqrl %[ov],%z[op],%[u]",
    51  				  ret, oldval, uaddr, oparg);
    52  		break;
    53  	case FUTEX_OP_OR:
    54  		__futex_atomic_op("amoor.w.aqrl %[ov],%z[op],%[u]",
    55  				  ret, oldval, uaddr, oparg);
    56  		break;
    57  	case FUTEX_OP_ANDN:
    58  		__futex_atomic_op("amoand.w.aqrl %[ov],%z[op],%[u]",
    59  				  ret, oldval, uaddr, ~oparg);
    60  		break;
    61  	case FUTEX_OP_XOR:
    62  		__futex_atomic_op("amoxor.w.aqrl %[ov],%z[op],%[u]",
    63  				  ret, oldval, uaddr, oparg);
    64  		break;
    65  	default:
    66  		ret = -ENOSYS;
    67  	}
    68  
    69  	if (!ret)
    70  		*oval = oldval;
    71  
    72  	return ret;
    73  }
    74  
    75  static inline int
    76  futex_atomic_cmpxchg_inatomic(u32 *uval, u32 __user *uaddr,
    77  			      u32 oldval, u32 newval)
    78  {
    79  	int ret = 0;
    80  	u32 val;
```
x86_64 的实现：
```c
    47  
    48  static __always_inline int arch_futex_atomic_op_inuser(int op, int oparg, int *oval,
    49  						       u32 __user *uaddr)
    50  {
    51  	scoped_user_rw_access(uaddr, Efault) {
    52  		switch (op) {
    53  		case FUTEX_OP_SET:
    54  			unsafe_atomic_op1("xchgl %0, %2", oval, uaddr, oparg, Efault);
    55  			break;
    56  		case FUTEX_OP_ADD:
    57  			unsafe_atomic_op1(LOCK_PREFIX "xaddl %0, %2", oval, uaddr, oparg, Efault);
    58  			break;
    59  		case FUTEX_OP_OR:
    60  			unsafe_atomic_op2("orl %4, %3", oval, uaddr, oparg, Efault);
    61  			break;
    62  		case FUTEX_OP_ANDN:
    63  			unsafe_atomic_op2("andl %4, %3", oval, uaddr, ~oparg, Efault);
    64  			break;
    65  		case FUTEX_OP_XOR:
    66  			unsafe_atomic_op2("xorl %4, %3", oval, uaddr, oparg, Efault);
    67  			break;
    68  		default:
    69  			return -ENOSYS;
    70  		}
    71  	}
    72  	return 0;
    73  Efault:
    74  	return -EFAULT;
    75  }
    76  
    77  static inline int futex_atomic_cmpxchg_inatomic(u32 *uval, u32 __user *uaddr,
    78  						u32 oldval, u32 newval)
    79  {
    80  	int ret = 0;
    81  
    82  	scoped_user_rw_access(uaddr, Efault) {
    83  		asm_inline volatile("\n"
    84  				    "1:\t" LOCK_PREFIX "cmpxchgl %3, %2\n"
    85  				    "2:\n"
    86  				    _ASM_EXTABLE_TYPE_REG(1b, 2b, EX_TYPE_EFAULT_REG, %0)
    87  				    : "+r" (ret), "=a" (oldval), "+m" (*uaddr)
    88  				    : "r" (newval), "1" (oldval)
    89  				    : "memory");
    90  		*uval = oldval;
    91  	}
    92  	return ret;
```
