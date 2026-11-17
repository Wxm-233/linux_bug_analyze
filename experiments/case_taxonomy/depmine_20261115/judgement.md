# 60 个抽样提交的判断

## 形态 A

- `721a73e30c9e` mm/sparse-vmemmap: fix DAX vmemmap accounting with optimization：**不是**。DAX vmemmap 统计数，与架构差异无关
- `099dd6878b9b` mm/swap: fix pte_same_as_swp() not removing uffd-wp bit when compare：**不是**。比较交换项时没去掉 uffd-wp 位，公共逻辑错误，所有支持 uffd-wp 的架构都一样
- `bd1f2b2ace84` mm/rmap: handle device-exclusive entries correctly in page_vma_mkclean_one()：**不是**。device-exclusive 条目没处理，公共逻辑
- `fac35ba763ed` mm/hugetlb: fix races when looking up a CONT-PTE/PMD size hugetlb page：**是**（P3，公共→架构，arm64）。公共层 follow_page 假设 hugetlb 只在 PMD/PUD 级，用了普通 pte 锁；arm64 支持 CONT-PTE/CONT-PMD 大页，锁不对。缺的是按大页形式取锁的检查（huge_pte_offset/huge_pte_lock）
- `44c6cb9fe988` KVM: guest_memfd: Allow mmap() on guest_memfd for x86 VMs with private memory：**不是**。放开 x86 guest_memfd 的 mmap，是功能调整
- `8d60902f16e2` ACPI: property: Polish ignoring bad data nodes：**不是**。ACPI 代码清理
- `4a3591287fb7` entry: Fix seccomp bypass after ptrace with TSYNC：**不是**。通用 entry 的竞态（缓存的 work 变量），与架构差异无关
- `ad1ac596e8a8` mm/migration: fix potential pte_unmap on an not mapped pte：**说不清**（None，公共→架构，HIGHPTE 架构（推断））。公共层假设 ptep 总是由 pte_offset_map 映射过，对 hugetlb 的 ptep 调 pte_unmap。后果只在 HIGHPTE（32 位）配置上出现，但提交说明没提架构
- `fed15f1345dc` mm/hugetlb: pre-allocate pgtable pages for uffd wr-protects：**不是**。hugetlb 的 uffd-wp 没预分配页表，公共逻辑
- `4d936f10ff80` irqchip/sifive-plic: Probe plic driver early for Allwinner D1 platform：**不是**。Allwinner D1 平台启动顺序（PLIC 驱动），单平台问题
- `26e7888a0c89` mm/memory: fix PMD/PUD checks in follow_pfnmap_start()：**是**（P1，公共→架构，loongarch）。公共层对非 present 的 PMD 调 pmd_leaf()，以为会返回假；loongarch 的 pmd_leaf 只看 _PAGE_HUGE，而交换项总带这一位。缺的是先查 pmd_present
- `0f6925b3e8da` virtio_net: Do not pull payload in skb->head：**不是**。virtio_net 性能回退
- `5cd474e57368` arm64: sdei: abort running SDEI handlers during crash：**不是**。arm64 SDEI 固件驱动的崩溃清理，单架构
- `ce732a7520b0` x86: kmsan: handle CPU entry area：**是**（P6，公共→架构，x86）。KMSAN 公共层假设内核地址都有通用的元数据映射；x86 的 CPU entry area 不在其中，返回 NULL 后递归告警。修复加了架构钩子 arch_kmsan_get_meta_or_null
- `4d4b6d66db63` mm,unmap: avoid flushing TLB in batch if PTE is inaccessible：**不是**。TLB 批量刷新的性能优化
- `3faa3ebc89c1` mm/page_idle: handle device-exclusive entries correctly in page_idle_clear_pte_refs_one()：**不是**。device-exclusive 条目没处理，公共逻辑
- `22061a1ffabd` mm/thp: unmap_mapping_page() to fix THP truncate_cleanup_page()：**不是**。THP 截断和解映射的竞态；提到 powerpc 只是设计取舍
- `dae8dda341d2` tracing: Fix subbuf resize races with trace_pipe_raw readers：**不是**。ring buffer 子缓冲区调整大小的竞态
- `c5e1a1eb9279` iommu/amd: Simplify and Consolidate Virtual APIC (AVIC) Enablement：**不是**。AMD IOMMU AVIC 启用流程
- `43e7f189769c` mm/huge_memory: use correct flags for device private PMD entry：**是**（P1，公共→架构，x86）。公共层对非 present 的 PMD（device-private 交换项）调 pmd_write()；x86 上 _PAGE_SWP_SOFT_DIRTY 与 _PAGE_RW 是同一位，于是把软脏位当成了可写位。缺的是按条目类型选访问函数

## 形态 B

- `92424801261d` bpf: Fix reg_set_min_max corruption of fake_reg：**不是**。BPF 校验器寄存器状态
- `0a744cceebd0` firmware: qcom: scm: Fix missing read barrier in qcom_scm_is_available()：**不是**。驱动里屏障没配对，是代码正确性问题，与边界无关
- `dde30854bddf` mm/debug_vm_pgtable: clear page table entries at destroy_args()：**不是**。页表测试退出时没清页表项；在 ppc64 上观察到，但问题是通用的
- `5c5f0468d172` mm/vmalloc: fix data race in show_numa_info()：**不是**。vmalloc 信息显示的数据竞争
- `a0fcaaed0c46` ring-buffer: Fix race between reset page and reading page：**不是**。ring buffer 读写竞态
- `6455b6163d8c` ring-buffer: Fix race while reader and writer are on the same page：**不是**。ring buffer 缺写屏障，只在 arm64 弱内存序上出现；跨架构表现，但不是边界依赖
- `c0474a606ecb` iommu/vt-d: Invalidate PASID cache when root/context entry changed：**不是**。Intel IOMMU 的 PASID 缓存失效，硬件规范
- `65529295607f` mm/rmap: handle device-exclusive entries correctly in try_to_unmap_one()：**不是**。device-exclusive 条目没处理，公共逻辑
- `cb0f01beb166` mm/mprotect: fix dax pud handlings：**是**（P3，公共→架构，x86_64、ppc64）。mprotect 的公共路径从没处理过 PUD 大页（以为不会有）；只有支持 PUD DAX 的 x86_64、ppc64 会走到，报 bad pud
- `a4a118f2eead` hugetlbfs: flush TLBs correctly after huge_pmd_unshare：**不是**。huge_pmd_unshare 后漏刷 TLB，对所有支持 PMD 共享的架构都一样
- `175e476b8cdf` netfilter: x_tables: Use correct memory barriers.：**不是**。x_tables 屏障太弱，在 MIPS64 上出错；跨架构表现，但不是边界依赖
- `faeb2831b517` mm: set folio swapbacked iff folios are dirty in try_to_unmap_one：**不是**。lazyfree 大 folio 的处理
- `382e6e177bc1` irqchip/gic-v3: Workaround inconsistent PMR setting on NMI entry：**不是**。arm64 entry 与 GICv3 驱动之间的 PMR 设置，都只在 arm 上
- `8c5b3a8adad2` mm/debug_vm_pgtable: fix corrupted page flag：**是**（P4，公共→架构，arm64）。公共测试代码假设 set_pte_at() 没有副作用；arm64 的 set_pte_at 在给执行权限时会设页标志 PG_arch_1，页释放后被查出 bad page。缺的是 flush_dcache_page 清标志
- `9add2cc22de6` mm/migrate_device: fix cache flush when replacing huge zero PMD：**是**（P2，公共→架构，缓存有别名的架构（目前无受影响者））。公共层给 flush_cache_page() 传错了参数和范围；只在 flush_cache_* 非空的架构（如 32 位 ARM）有后果，提交说明称目前没有架构同时开 THP 迁移，属潜在问题
- `19b482c29b6f` mm: shmem: fix missing cache flush in shmem_mfill_atomic_pte()：**是**（P2，公共→架构，缓存有别名的架构）。shmem 的 userfaultfd 路径漏了 flush_dcache_page；该钩子在 x86/arm64/riscv 上是空的，只在缓存有别名的架构上出错
- `194b3348bdbb` iommu/vt-d: Fix PASID directory pointer coherency：**不是**。Intel IOMMU 页表遍历一致性，硬件能力
- `0cef0bb836e3` mm: clear uffd-wp PTE/PMD state on mremap()：**不是**。mremap 后 uffd-wp 状态不一致，公共逻辑
- `8ce720d5bd91` mm/hugetlb: fix excessive IPI broadcasts when unsharing PMD tables using mmu_gather：**不是**。IPI 广播太多，性能
- `7f9c9b607dc2` mm: rmap: fix cache flush on THP pages：**是**（P2，公共→架构，缓存有别名的架构）。对 THP 只用 flush_cache_page() 刷了一页；只在虚拟索引缓存的架构上有后果，提交说明说没发现实际问题

## 形态 C

- `8cfe148a7136` kvm/arm64: rework guest entry logic：**是**（P5，架构→公共，arm64（同系列也改了其他架构））。arm64 KVM 在 RCU 扩展静止状态里开中断，违反公共层的约定（中断入口不会唤醒 RCU），中断处理时 RCU 没在观察
- `1037d186edfc` openrisc: Implement fixmap to fix earlycon：**是**（P5，架构→公共，openrisc）。openrisc 去掉了 early ioremap，而公共层 earlycon 依赖它；架构缺了公共层隐含依赖的能力
- `e19d4ebc536d` alpha: add full ioread64/iowrite64 implementation：**不是**。alpha 缺 ioread64 定义，链接时就报错，属构建问题
- `58661a30f1bc` riscv: Flush the instruction cache during SMP bringup：**说不清**（None，架构→公共，riscv）。riscv 的指令缓存刷新 IPI 只发给在线 CPU，新上线的 CPU 可能看到旧指令。是否算公共层约定（代码修改对新 CPU 可见）说不清
- `b1b93cb7e794` powerpc/nohash: Fix __ptep_set_access_flags() and ptep_set_wrprotect()：**不是**。powerpc 8xx 页表位，架构内部
- `5b0870931371` KVM: arm64: Fix host's ZCR_EL2 restore on nVHE：**不是**。arm64 nVHE 寄存器顺序，架构内部
- `ea64baacbc36` arm64/signal: Flush FPSIMD register state when disabling streaming mode：**不是**。arm64 信号处理的 FPSIMD 状态，架构内部
- `f0293cd1f4fc` riscv: mm: Implement pmdp_collapse_flush for THP：**是**（P4，公共→架构，riscv）。通用的 pmdp_collapse_flush() 假设 flush_tlb_range() 也会清掉缓存的非叶子页表项；riscv 按地址的 SFENCE 只清叶子项，THP 合并后反复缺页。修复给 riscv 加了自己的实现
- `b7795074a046` parisc: Optimize per-pagetable spinlocks：**不是**。parisc 页表锁重构，架构内部
- `b7d9d2e3a8ab` arm64: mm: __ptep_set_access_flags must hint correct TTL：**不是**。arm64 TLB 刷新的级别提示，调用者是 arm64 自己的大页辅助函数，架构内部
- `7e1864332fbc` riscv: fix race when vmap stack overflow：**不是**。riscv vmap 栈溢出的竞态，架构内部
- `8d736482749f` riscv: add icache flush for nommu sigreturn trampoline：**不是**。riscv nommu 信号跳板没刷指令缓存，架构自己的代码
- `496e0f706b8a` KVM: s390: Fix unlikely NULL gmap dereference：**是**（P5，架构→公共，s390）。公共层在创建 vCPU 文件描述符之后才调 kvm_arch_vcpu_postcreate()；s390 假设 postcreate 一定先于运行，恶意用户可抢先运行导致空指针
- `b49f700668ff` riscv: mm: fix regression due to update_mmu_cache change：**不是**。riscv update_mmu_cache 在某款 SoC 上的回退，架构内部
- `1665c027afb2` powerpc/64s: Reconnect tlb_flush() to hash__tlb_flush()：**不是**。powerpc hash MMU 的 tlb_flush 被误删，架构内部
- `f64c723741c9` bpf: Replace scratch PTE atomically when allocating arena pages：**是**（P4，公共→架构，arm64）。BPF arena 公共代码直接把有效的页表项改成另一个有效值；arm64 要求先清、刷 TLB 再写（break-before-make）。修复加了架构钩子 flush_tlb_before_set
- `49c87f767774` arm64: hugetlb: Fix huge_ptep_get_and_clear() for non-present ptes：**是**（P1，架构→公共，arm64）。公共层 move_huge_pte() 会对非 present 的项调 huge_ptep_get_and_clear()；arm64 的实现假设项是 present（靠 PTE_CONT 位判断大小），对标记项和迁移项判错
- `835e5ac3f98e` riscv: Fix huge_ptep_set_wrprotect when PTE is a NAPOT：**不是**。riscv NAPOT 写保护要先清再刷，架构内部（提交说明提到 arm64 也这样做，是横向线索）
- `410982303772` arm64: hugetlb: Restore TLB invalidation for BBM on contiguous ptes：**不是**。arm64 大页 BBM 序列内部漏了 TLB 失效，架构内部
- `213aa670153e` parisc: Delay write-protection until mark_rodata_ro() call：**是**（P5，架构→公共，parisc）。公共层约定 __ro_after_init 段在 mark_rodata_ro() 之前可写（jump_label 依赖这一点）；parisc 提前写保护，启动失败
