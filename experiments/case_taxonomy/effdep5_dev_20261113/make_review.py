"""out/review_CUR_riscv.md: manual review of current-version vertical candidates (criteria 四.4, amendment 1.3).
The 2 candidates with a horizontal difference are the review set; the other 30 are looked at as an extra, reported separately."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
NOT = "不是"
DEP = "真实依赖，当前满足"
CTRL = "普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作"
SPECIAL = {
 ("hugetlb_fault", "update_mmu_cache"): (NOT, "ret = 0 是返回码，随后 goto out_mutex；vma_end_read 是释放锁，与 update_mmu_cache 的效果无关"),
 ("hugetlb_fault", "update_mmu_cache_range"): (NOT, "同上"),
 ("hugetlb_fault", "set_huge_pte_at"): (NOT, "同上"),
 ("do_swap_page", "pte_modify"): (DEP, "调用 pte_modify(pte, PAGE_NONE) 后置 rwp_restore = true，跳过 do_wp_page（写时复制），依赖 pte_modify 保留 _PAGE_UFFD 位（源码注释写明）。支持 USERFAULTFD_RWP 的三个架构（x86 明确把 _PAGE_UFFD 放进 _PAGE_CHG_MASK；arm64、riscv 的掩码保留权限位以外的所有位）都满足。2026-07 的 763f43865fc4 修过同一类依赖在其他路径上的缺失。以后新架构支持该特性时需满足这条依赖"),
 ("__irq_set_trigger", "mask_irq"): (NOT, "unmask = 1 记录“之后要恢复”，是状态记录"),
 ("_vm_unmap_aliases", "max"): (NOT, "flush = 1 表示“要刷”，方向相反（触发而不是跳过）"),
 ("_vm_unmap_aliases", "min"): (NOT, "同上"),
 ("acpi_os_read_memory", "acpi_os_ioremap"): (NOT, "unmap = true 记录映射来源，之后对称释放"),
 ("acpi_os_write_memory", "acpi_os_ioremap"): (NOT, "同上"),
}
rows_q, rows_x = [], []
for i, c in enumerate(d["candidates_list"], 1):
    v, why = SPECIAL.get((c["fn"], c["interface"]), (NOT, CTRL))
    row = f"| {i} | `{c['fn']}` {c['file']}:{c['call_line']} | `{c['interface']}` | `{c['flag']} = {c['const']}` | {'、'.join(c['skipped_all'][:3])} | {v} | {why} |"
    (rows_q if c["qualified"] else rows_x).append(row)
H = "| 排名 | 位置 | 接口 | 标志 | 被跳过的调用 | 判断 | 理由 |\n|---|---|---|---|---|---|---|"
out = ["# 当前版本 riscv：纵向候选人工核对", "",
       f"修订 2 之后，共有 {d['candidates']} 个候选，其中有横向差异的 {d['qualified']} 个。按判据核对的是这 {d['qualified']} 个；其余 {d['candidates'] - d['qualified']} 个作为额外参考也看了，单独列出。判断标准见修订 1 第 3 条。核对人 Claude，读的是 `/root/repos/linux`（7.3-rc2）。", "",
       "## 有横向差异的（判据要求核对的）", "", H] + rows_q + ["", "## 其余候选（额外参考）", "", H] + rows_x
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(rows_q), len(rows_x))
