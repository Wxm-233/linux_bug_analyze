"""Claude's design-side judgements (criteria 五), written after reading show_design.txt. Windows or WSL python.

    python judge_design.py -> design_judgement.json, design_positives.json, counterexamples.json
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
Y, U, N, F = "是", "说不清", "不是", "同族非架构"

J = {
    # ---- 是 ----
    "6829e274a623": (Y, "D1", "dma_alloc_coherent 返回的缓冲区在其他架构上总是全零，驱动依赖这一点，还可能经 dma_mmap 给用户；arm64 只在带 __GFP_ZERO 时清零。修复：arm64 无条件清零"),
    "2545e5da080b": (Y, "D2", "copy_from_user 的公共约定：没拷到的部分要清零。asm-generic 实现在 access_ok 失败时不清零；用到它的架构把未初始化内容交给调用方"),
    "8630c32275ba": (Y, "D2", "同 D2 系列（Al Viro 2016-09），avr32 实现"),
    "e33d1f6f72cc": (Y, "D2", "同 D2 系列，nios2 实现"),
    "ae7cc577ec2a": (Y, "D2", "同 D2 系列，mn10300 实现"),
    "8ae95ed4ae5f": (Y, "D2", "同 D2 系列，metag 实现"),
    "a5e541f796f1": (Y, "D2", "同 D2 系列，ia64 实现"),
    "eb47e0293baa": (Y, "D2", "同 D2 系列，cris 实现"),
    "e89f5b370153": (Y, "D3", "公共 dma_alloc_attrs 去掉 __GFP_ZERO，假设各实现总会清零；arc、s390 的实现不带这个标志就不清零，驱动拿到脏缓冲区。修复：不再去掉标志"),
    "dd65a941f6ba": (Y, "D4", "arm64 IOMMU 的 DMA_ATTR_FORCE_CONTIGUOUS 路径从 CMA 取页，dma_alloc_from_contiguous 不认 __GFP_ZERO，缓冲区没清零就交给驱动/用户"),
    "a1da439cc0d9": (Y, "D5", "通用 remap 分配器（kernel/dma/remap.c 的 arch_dma_alloc，只在选了 DMA_DIRECT_REMAP 的架构上用）改用 __dma_direct_alloc_pages 后既不设 dma_handle 也不清零"),
    # ---- 说不清 ----
    "34f19ff1b5a0": (U, None, "powerpc 紧急栈的 thread_info 没初始化，公共 nmi_enter 读到垃圾 preempt_count。是“公共约定（thread_info 已初始化）+ 架构实现不满足”，但约定是“有效初始值”不是“清零”，边界上"),
    # ---- 同族非架构 ----
    "5c7a3a3d20a4": (F, None, "timer_settime 的 oldval 依赖 k_clock->timer_get 填满；各时钟类型的实现不全写，系统调用层原来清零、重构后漏了。实现选择是时钟类型，与架构无关"),
    "0f181f9fbea8": (F, None, "init_on_free 要求对象全零；SLUB 批量分配路径没擦 freelist 指针。是同一实现里的另一条路径，与架构无关"),
    "26dca996ea7b": (F, None, "init_on_free 要求对象全零；Generic KASAN 隔离区在清零之后又写入元数据。实现选择是 KASAN 模式，Generic 在各主流架构都有"),
    # ---- 不是 ----
    "b75f4c9afac2": (N, None, "s390 KVM 自己的 STSI 结构体保留字段"),
    "f2ae45edbca7": (N, None, "s390 KVM 自己的中断状态复位"),
    "dfbca61af0b6": (N, None, "arm64 hibernate 分配失败处理"),
    "e3b6a02816eb": (N, None, "parisc 自己的 get_memblock 给自己的页表用，没有公共请求"),
    "cbfc6c9184ce": (N, None, "KVM x86 越界读"),
    "af54aed94bf3": (N, None, "去掉 balloon 页清零（性能）"),
    "e10237cc76ef": (N, None, "kthread 自己的结构体"),
    "6b7e633fe9c2": (N, None, "去掉多余清零"),
    "636e645f1f2a": (N, None, "ARM NOMMU 内部数组残留"),
    "09e35a4a1ca8": (N, None, "gup_benchmark 失败处理"),
    "0a0b98734479": (N, None, "compat adjtimex 结构体字段未初始化，属结构体忘了清零"),
    "128227e7fe40": (N, None, "__GFP_ZERO 与构造函数冲突的告警"),
    "d3f66e4116af": (N, None, "bpf 自己的缓冲区"),
    "2af8ff291848": (N, None, "khugepaged collapse_shmem 漏清空洞，与实现选择无关"),
    "32043fa065b5": (N, None, "x86 mtrr 结构体泄漏"),
    "4af396ae4836": (N, None, "bpf build_id"),
    "3a33d030daaa": (N, None, "KVM vmx 自己的结构体"),
    "98d90582be2e": (N, None, "SVM AVIC"),
    "a90118c445cc": (N, None, "x86 boot_params 清理写法（编译告警）"),
    "8a9093c79863": (N, None, "net sched"),
    "edd4fa37baa6": (N, None, "KVM x86 memslot"),
    "56df70a63ed5": (N, None, "KSM 空指针"),
    "8982ae527fbe": (N, None, "kzfree 防编译器优化掉 memset"),
    "d81ae8aac85c": (N, None, "uclamp 初始化"),
    "ce5716c61852": (N, None, "清零做了，问题是 HW_TAGS 指针标签导致误报"),
    "17d8beda277a": (N, None, "bpf_iter"),
    "68d54ceeec0e": (N, None, "MTE 零页标签已清，问题是标志位"),
    "85d703746154": (N, None, "KVM arm64 vcpu 复位"),
    "ff40e51043af": (N, None, "bpf lockdown"),
    "4f13d471e5d1": (N, None, "SEV 长度"),
    "93c2cdc975aa": (N, None, "x86 xstate 头栈上未清零，架构内部"),
    "7f049fbdd57f": (N, None, "x86 LBR 缓冲区，架构内部"),
    "69e5d322a2fb": (N, None, "page_poison 与 init_on_alloc 配置交互造成误报，不是漏清零"),
    "0594c58161b6": (N, None, "xen x86 trap"),
    "44cad52cc14a": (N, None, "x86 ptrace xmm 清理"),
    "08999b2489b4": (N, None, "sgx"),
    "19b482c29b6f": (N, None, "shmem 刷缓存（P2）"),
    "be77354a3d7e": (N, None, "bpf"),
    "b4e61fc031b1": (N, None, "memory-failure 回退"),
    "d22d2474e395": (N, None, "SEV ioctl 自己的结构体"),
    "ec6d0dde71d7": (N, None, "powerpc execve 寄存器"),
    "0424a7dfe912": (N, None, "resctrl"),
    "fdb54d96600a": (N, None, "HW_TAGS 初始化写过了 slub_debug 红区，是多清，不是漏清"),
    "079082c60aff": (N, None, "tcx"),
    "8e7b58c27b3c": (N, None, "ring-buffer"),
}
CALIB = {
    "5bebe8de1926": (Y, "X1", "校准例。__GFP_ZEROTAGS 请求清零；post_alloc_hook 调 tag_clear_highpage 后把 init 设为 false；通用空实现什么都不做，零页内容没清就映射给用户"),
    "6c2f761dad78": (Y, "K1", "校准例。调用方用 KASAN_VMALLOC_INIT 要求清零；HW_TAGS 下被调函数几条提前返回的路径不清零"),
}
CEX = [
    {"id": "C1", "type": "R1", "rev": "e89f5b370153^", "loc": "lib/dma-direct.c:100", "for": "D3",
     "why": "dma_direct_alloc 无条件 memset(ret, 0, size)；用 dma-direct 的架构上，公共层去掉 __GFP_ZERO 无害"},
    {"id": "C2", "type": "R1", "rev": "2545e5da080b^", "loc": "arch/x86/lib/usercopy_32.c:683-690（另 usercopy_64.c:86 尾部清零）", "for": "D2",
     "why": "x86 的 _copy_from_user 在 access_ok 失败时整段清零，部分失败时 copy_user_handle_tail 清尾部"},
    {"id": "C3", "type": "R3", "rev": "5bebe8de1926^", "loc": "arch/arm64/mm/fault.c:964-965", "for": "X1",
     "why": "arm64 只在 VM_MTE 时加 __GFP_ZEROTAGS；VM_MTE 意味着硬件支持 MTE，tag_clear_highpage 会真的清零，和“跳过”的那个选择互斥"},
    {"id": "C4", "type": "R1", "rev": "5bebe8de1926^", "loc": "mm/page_alloc.c:1833-1837", "for": "X1",
     "why": "kasan_unpoison_pages 之后只有 kasan_has_integrated_init() 为真才跳过 kernel_init_pages，即 HW_TAGS 自己做了初始化"},
]


def main():
    d = json.loads((HERE / "design.json").read_text(encoding="utf-8"))
    shown = [ln.split()[0] for ln in (HERE / "show_design.txt").read_text(encoding="utf-8-sig").split("\n")
             if len(ln) > 13 and ln[12] == " " and all(ch in "0123456789abcdef" for ch in ln[:12])]
    assert set(shown) == set(J), (set(shown) ^ set(J))
    meta = {c["commit"]: c for c in d}
    rows = [{"commit": k, "date": meta[k]["date"], "subject": meta[k]["subject"], "fixes": meta[k]["fixes"],
             "verdict": v, "rootcause": rc, "why": w} for k, (v, rc, w) in J.items()]
    cmeta = {"5bebe8de1926": ("2025-11-18", "mm/huge_memory: Fix initialization of huge zero folio", ["adfb6609c680"]),
             "6c2f761dad78": ("2022-07-03", "kasan: fix zeroing vmalloc memory with HW_TAGS", ["23689e91fb22"])}
    rows += [{"commit": k, "date": cmeta[k][0], "subject": cmeta[k][1], "fixes": cmeta[k][2], "in_design_json": k in meta,
              "verdict": v, "rootcause": rc, "why": w, "calibration": True} for k, (v, rc, w) in CALIB.items()]
    (HERE / "design_judgement.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    pos = [{"commit": r["commit"], "fixes": r["fixes"], "rootcause": r["rootcause"], "what": r["why"]} for r in rows if r["verdict"] == Y]
    (HERE / "design_positives.json").write_text(json.dumps(pos, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "counterexamples.json").write_text(json.dumps(CEX, indent=1, ensure_ascii=False), encoding="utf-8")
    sampled = [r for r in rows if not r.get("calibration")]
    c = Counter(r["verdict"] for r in sampled)
    rcs = sorted({r["rootcause"] for r in rows if r["verdict"] == Y})
    print("sampled", len(sampled), dict(c), "| yes root causes (incl. calibration):", rcs, "| counterexamples:", len(CEX),
          Counter(x["type"] for x in CEX))


if __name__ == "__main__":
    main()
