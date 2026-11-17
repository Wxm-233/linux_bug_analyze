"""depmine criteria 五/六: my judgements of the 60 sampled commits -> judgement.json, stats.json, judgement.md

Judged from the commit message and the matched hunks (show_sample.txt), before any other analysis. One annotator (Claude).
verdict: Y = 是, N = 不是, U = 说不清
dir: c2a = 公共层依赖架构接口的假设；a2c = 架构实现依赖/违反公共层的约定
pat: P1 present 前置条件没检查; P2 缓存别名架构的刷缓存; P3 大页级别/形式假设; P4 架构接口的副作用或效果范围;
     P5 调用顺序/时机约定; P6 架构特有地址区域
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

J = [
    # form A
    ("A", "721a73e30c9e", "N", "", "", "", "DAX vmemmap 统计数，与架构差异无关"),
    ("A", "099dd6878b9b", "N", "", "", "", "比较交换项时没去掉 uffd-wp 位，公共逻辑错误，所有支持 uffd-wp 的架构都一样"),
    ("A", "bd1f2b2ace84", "N", "", "", "", "device-exclusive 条目没处理，公共逻辑"),
    ("A", "fac35ba763ed", "Y", "c2a", "P3", "arm64",
     "公共层 follow_page 假设 hugetlb 只在 PMD/PUD 级，用了普通 pte 锁；arm64 支持 CONT-PTE/CONT-PMD 大页，锁不对。缺的是按大页形式取锁的检查（huge_pte_offset/huge_pte_lock）"),
    ("A", "44c6cb9fe988", "N", "", "", "", "放开 x86 guest_memfd 的 mmap，是功能调整"),
    ("A", "8d60902f16e2", "N", "", "", "", "ACPI 代码清理"),
    ("A", "4a3591287fb7", "N", "", "", "", "通用 entry 的竞态（缓存的 work 变量），与架构差异无关"),
    ("A", "ad1ac596e8a8", "U", "c2a", "", "HIGHPTE 架构（推断）",
     "公共层假设 ptep 总是由 pte_offset_map 映射过，对 hugetlb 的 ptep 调 pte_unmap。后果只在 HIGHPTE（32 位）配置上出现，但提交说明没提架构"),
    ("A", "fed15f1345dc", "N", "", "", "", "hugetlb 的 uffd-wp 没预分配页表，公共逻辑"),
    ("A", "4d936f10ff80", "N", "", "", "", "Allwinner D1 平台启动顺序（PLIC 驱动），单平台问题"),
    ("A", "26e7888a0c89", "Y", "c2a", "P1", "loongarch",
     "公共层对非 present 的 PMD 调 pmd_leaf()，以为会返回假；loongarch 的 pmd_leaf 只看 _PAGE_HUGE，而交换项总带这一位。缺的是先查 pmd_present"),
    ("A", "0f6925b3e8da", "N", "", "", "", "virtio_net 性能回退"),
    ("A", "5cd474e57368", "N", "", "", "", "arm64 SDEI 固件驱动的崩溃清理，单架构"),
    ("A", "ce732a7520b0", "Y", "c2a", "P6", "x86",
     "KMSAN 公共层假设内核地址都有通用的元数据映射；x86 的 CPU entry area 不在其中，返回 NULL 后递归告警。修复加了架构钩子 arch_kmsan_get_meta_or_null"),
    ("A", "4d4b6d66db63", "N", "", "", "", "TLB 批量刷新的性能优化"),
    ("A", "3faa3ebc89c1", "N", "", "", "", "device-exclusive 条目没处理，公共逻辑"),
    ("A", "22061a1ffabd", "N", "", "", "", "THP 截断和解映射的竞态；提到 powerpc 只是设计取舍"),
    ("A", "dae8dda341d2", "N", "", "", "", "ring buffer 子缓冲区调整大小的竞态"),
    ("A", "c5e1a1eb9279", "N", "", "", "", "AMD IOMMU AVIC 启用流程"),
    ("A", "43e7f189769c", "Y", "c2a", "P1", "x86",
     "公共层对非 present 的 PMD（device-private 交换项）调 pmd_write()；x86 上 _PAGE_SWP_SOFT_DIRTY 与 _PAGE_RW 是同一位，于是把软脏位当成了可写位。缺的是按条目类型选访问函数"),
    # form B
    ("B", "92424801261d", "N", "", "", "", "BPF 校验器寄存器状态"),
    ("B", "0a744cceebd0", "N", "", "", "", "驱动里屏障没配对，是代码正确性问题，与边界无关"),
    ("B", "dde30854bddf", "N", "", "", "", "页表测试退出时没清页表项；在 ppc64 上观察到，但问题是通用的"),
    ("B", "5c5f0468d172", "N", "", "", "", "vmalloc 信息显示的数据竞争"),
    ("B", "a0fcaaed0c46", "N", "", "", "", "ring buffer 读写竞态"),
    ("B", "6455b6163d8c", "N", "", "", "", "ring buffer 缺写屏障，只在 arm64 弱内存序上出现；跨架构表现，但不是边界依赖", "xarch_memory_order"),
    ("B", "c0474a606ecb", "N", "", "", "", "Intel IOMMU 的 PASID 缓存失效，硬件规范"),
    ("B", "65529295607f", "N", "", "", "", "device-exclusive 条目没处理，公共逻辑"),
    ("B", "cb0f01beb166", "Y", "c2a", "P3", "x86_64、ppc64",
     "mprotect 的公共路径从没处理过 PUD 大页（以为不会有）；只有支持 PUD DAX 的 x86_64、ppc64 会走到，报 bad pud"),
    ("B", "a4a118f2eead", "N", "", "", "", "huge_pmd_unshare 后漏刷 TLB，对所有支持 PMD 共享的架构都一样"),
    ("B", "175e476b8cdf", "N", "", "", "", "x_tables 屏障太弱，在 MIPS64 上出错；跨架构表现，但不是边界依赖", "xarch_memory_order"),
    ("B", "faeb2831b517", "N", "", "", "", "lazyfree 大 folio 的处理"),
    ("B", "382e6e177bc1", "N", "", "", "", "arm64 entry 与 GICv3 驱动之间的 PMR 设置，都只在 arm 上"),
    ("B", "8c5b3a8adad2", "Y", "c2a", "P4", "arm64",
     "公共测试代码假设 set_pte_at() 没有副作用；arm64 的 set_pte_at 在给执行权限时会设页标志 PG_arch_1，页释放后被查出 bad page。缺的是 flush_dcache_page 清标志"),
    ("B", "9add2cc22de6", "Y", "c2a", "P2", "缓存有别名的架构（目前无受影响者）",
     "公共层给 flush_cache_page() 传错了参数和范围；只在 flush_cache_* 非空的架构（如 32 位 ARM）有后果，提交说明称目前没有架构同时开 THP 迁移，属潜在问题"),
    ("B", "19b482c29b6f", "Y", "c2a", "P2", "缓存有别名的架构",
     "shmem 的 userfaultfd 路径漏了 flush_dcache_page；该钩子在 x86/arm64/riscv 上是空的，只在缓存有别名的架构上出错"),
    ("B", "194b3348bdbb", "N", "", "", "", "Intel IOMMU 页表遍历一致性，硬件能力"),
    ("B", "0cef0bb836e3", "N", "", "", "", "mremap 后 uffd-wp 状态不一致，公共逻辑"),
    ("B", "8ce720d5bd91", "N", "", "", "", "IPI 广播太多，性能"),
    ("B", "7f9c9b607dc2", "Y", "c2a", "P2", "缓存有别名的架构",
     "对 THP 只用 flush_cache_page() 刷了一页；只在虚拟索引缓存的架构上有后果，提交说明说没发现实际问题"),
    # form C
    ("C", "8cfe148a7136", "Y", "a2c", "P5", "arm64（同系列也改了其他架构）",
     "arm64 KVM 在 RCU 扩展静止状态里开中断，违反公共层的约定（中断入口不会唤醒 RCU），中断处理时 RCU 没在观察"),
    ("C", "1037d186edfc", "Y", "a2c", "P5", "openrisc",
     "openrisc 去掉了 early ioremap，而公共层 earlycon 依赖它；架构缺了公共层隐含依赖的能力"),
    ("C", "e19d4ebc536d", "N", "", "", "", "alpha 缺 ioread64 定义，链接时就报错，属构建问题"),
    ("C", "58661a30f1bc", "U", "a2c", "", "riscv",
     "riscv 的指令缓存刷新 IPI 只发给在线 CPU，新上线的 CPU 可能看到旧指令。是否算公共层约定（代码修改对新 CPU 可见）说不清"),
    ("C", "b1b93cb7e794", "N", "", "", "", "powerpc 8xx 页表位，架构内部"),
    ("C", "5b0870931371", "N", "", "", "", "arm64 nVHE 寄存器顺序，架构内部"),
    ("C", "ea64baacbc36", "N", "", "", "", "arm64 信号处理的 FPSIMD 状态，架构内部"),
    ("C", "f0293cd1f4fc", "Y", "c2a", "P4", "riscv",
     "通用的 pmdp_collapse_flush() 假设 flush_tlb_range() 也会清掉缓存的非叶子页表项；riscv 按地址的 SFENCE 只清叶子项，THP 合并后反复缺页。修复给 riscv 加了自己的实现"),
    ("C", "b7795074a046", "N", "", "", "", "parisc 页表锁重构，架构内部"),
    ("C", "b7d9d2e3a8ab", "N", "", "", "", "arm64 TLB 刷新的级别提示，调用者是 arm64 自己的大页辅助函数，架构内部"),
    ("C", "7e1864332fbc", "N", "", "", "", "riscv vmap 栈溢出的竞态，架构内部"),
    ("C", "8d736482749f", "N", "", "", "", "riscv nommu 信号跳板没刷指令缓存，架构自己的代码"),
    ("C", "496e0f706b8a", "Y", "a2c", "P5", "s390",
     "公共层在创建 vCPU 文件描述符之后才调 kvm_arch_vcpu_postcreate()；s390 假设 postcreate 一定先于运行，恶意用户可抢先运行导致空指针"),
    ("C", "b49f700668ff", "N", "", "", "", "riscv update_mmu_cache 在某款 SoC 上的回退，架构内部"),
    ("C", "1665c027afb2", "N", "", "", "", "powerpc hash MMU 的 tlb_flush 被误删，架构内部"),
    ("C", "f64c723741c9", "Y", "c2a", "P4", "arm64",
     "BPF arena 公共代码直接把有效的页表项改成另一个有效值；arm64 要求先清、刷 TLB 再写（break-before-make）。修复加了架构钩子 flush_tlb_before_set"),
    ("C", "49c87f767774", "Y", "a2c", "P1", "arm64",
     "公共层 move_huge_pte() 会对非 present 的项调 huge_ptep_get_and_clear()；arm64 的实现假设项是 present（靠 PTE_CONT 位判断大小），对标记项和迁移项判错"),
    ("C", "835e5ac3f98e", "N", "", "", "", "riscv NAPOT 写保护要先清再刷，架构内部（提交说明提到 arm64 也这样做，是横向线索）"),
    ("C", "410982303772", "N", "", "", "", "arm64 大页 BBM 序列内部漏了 TLB 失效，架构内部"),
    ("C", "213aa670153e", "Y", "a2c", "P5", "parisc",
     "公共层约定 __ro_after_init 段在 mark_rodata_ro() 之前可写（jump_label 依赖这一点）；parisc 提前写保护，启动失败"),
]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def main():
    cand = json.loads((HERE / "candidates.json").read_text(encoding="utf-8"))
    samp = json.loads((HERE / "sample.json").read_text(encoding="utf-8"))
    subj = {c["commit"][:12]: c["subject"] for c in cand["commits"]}
    rows = []
    for t in J:
        f, h, v, d, p, a, why = t[:7]
        rows.append({"form": f, "commit": h, "subject": subj.get(h), "verdict": {"Y": "是", "N": "不是", "U": "说不清"}[v],
                     "direction": d or None, "pattern": p or None, "archs": a or None, "why": why, "tag": t[7] if len(t) > 7 else None})
    for f in "ABC":  # every sampled commit judged exactly once per form
        assert sorted(x["commit"] for x in rows if x["form"] == f) == sorted(h[:12] for h in samp[f]), f
    per = {}
    for f in "ABC":
        sel = [x for x in rows if x["form"] == f]
        y = sum(x["verdict"] == "是" for x in sel)
        u = sum(x["verdict"] == "说不清" for x in sel)
        N = cand["counts"][f]["after_dev_exclusion"]
        ci = wilson(y, len(sel))
        per[f] = {"n": len(sel), "yes": y, "unclear": u, "no": len(sel) - y - u, "ratio": round(y / len(sel), 3), "wilson95": ci,
                  "population": N, "est_yes": round(y / len(sel) * N, 1), "est_yes_range": [round(ci[0] * N, 1), round(ci[1] * N, 1)]}
    yes = [x for x in rows if x["verdict"] == "是"]
    pats = {}
    for x in yes:
        pats.setdefault(x["pattern"], []).append(x["commit"])
    dirs = {d: sum(x["direction"] == d for x in yes) for d in ("c2a", "a2c")}
    stats = {"scanned_commits": cand["scanned_commits"], "interfaces": cand["interfaces"], "counts": cand["counts"],
             "selfcheck": cand["selfcheck"], "per_form": per, "yes_total": len(yes),
             "unclear_total": sum(x["verdict"] == "说不清" for x in rows), "patterns": pats, "directions": dirs,
             "skip_then_flag_shape": 0, "model_calls": 0, "builds": 0, "new_bugs": 0, "new_suspects": 0}
    (HERE / "judgement.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    L = ["# 60 个抽样提交的判断", ""]
    for f in "ABC":
        L += [f"## 形态 {f}", ""]
        for x in rows:
            if x["form"] == f:
                extra = f"（{x['pattern']}，{'公共→架构' if x['direction'] == 'c2a' else '架构→公共' if x['direction'] == 'a2c' else ''}，{x['archs']}）" \
                    if x["verdict"] != "不是" else ""
                L.append(f"- `{x['commit']}` {x['subject']}：**{x['verdict']}**{extra}。{x['why']}")
        L.append("")
    (HERE / "judgement.md").write_text("\n".join(L), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("per_form", "yes_total", "unclear_total", "patterns", "directions")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
