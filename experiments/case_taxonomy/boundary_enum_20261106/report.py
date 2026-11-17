"""Render Chinese report from verified artifacts, without invented numbers."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
stats = json.loads((HERE / "stats.json").read_text(encoding="utf-8"))
arches = stats["architectures"]
symbols = json.loads((HERE / "symbols_riscv.json").read_text(encoding="utf-8"))
examples = {}
preferred = {"public_to_arch": ("flush_tlb_mm_range", "copy_to_user", "raw_spin_lock", "virt_to_phys"),
             "arch_to_public": ("memblock_alloc", "memblock_phys_alloc", "panic", "memcpy", "printk")}
for direction, names in preferred.items():
    choices = [s for s in symbols if s["direction"] == direction and s["kind"] == "function"]
    chosen = next((s for name in names for s in choices if s["name"] == name), choices[0])
    with gzip.open(HERE / "boundary_riscv.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            point = json.loads(line)
            if point["symbol_id"] == chosen["id"]:
                examples[direction] = (chosen, point)
                break

lines = ["# 构建矩阵与边界枚举", "", "我想先回答一个规模问题：在固定版本、固定配置里，公共代码与架构代码之间实际出现了多少符号引用。这里的边界符号是被另一侧使用的函数、宏、类型或数据对象；边界点是源代码中一次具体的调用、取地址、读写、宏展开或类型使用。这个实验只枚举边界，不判断这些地方是否有缺陷。", "",
         "## 输入与自测", "",
         "我使用既有 LLVM=1 构建，内核提交为 `df2908090cda368b01ff43709f51890076c56157`，配置为 riscv RV64、arm64、x86_64 的 defconfig。每批运行前校验源码状态、配置、编译数据库、生成头文件、工具和脚本摘要；没有改内核源码。", "",
         "冻结判据 `criteria.md` 的 SHA256 是 `692e96fbcd1b5135bfc0fcf7fb77cf455b769cbdc171169983cf7a759bccef30`。修订 1 只将长任务改为前台分批执行。", "",
         "自测通过：3 个 C 单元成功解析，19 点人工预期集合完全一致，重复头文件只计一次并保留两个单元证据，nm 汇编引用及 weak 覆盖断言通过。另有同名静态对象键的回归检查通过。我修复了 Cursor 不能直接作为字典键、不同遍历路径下的直接调用去重，以及 C 暂定对象定义未收录的问题，没有修改预期集合。`selftest/failure.txt` 是上轮失败的历史记录，当前状态见 `selftest/result.json`。", "",
         "## 枚举结果", "", "| 架构 | C 单元成功 | C 单元失败 | 边界符号 | 边界点 | 执行秒数 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
for a, r in arches.items():
    lines.append(f"| {a} | {r['parsed_units']} | {r['parse_failed_units']} | {r['symbols']} | {r['points']} | {r['measured_execution_seconds']:.1f} |")
lines += ["", "耗时为各次扫描与合并命令的实测时间之和，不含批次间阅读和编写报告的时间；RISC-V 最初 576 单元只有扫描循环耗时，不含启动核验时间。每个 C 单元都有成功或失败状态。合并后重新核对了明细去重、每个符号的使用次数及总数。", "",
          "符号按定义身份与方向计数；同名静态符号用 USR 和定义位置区分。同一源码点被多个编译单元包含时只计一次，`units` 保留所有单元证据。按子系统的分布见 `stats.json` 中各架构的 `by_subsystem`；同一符号可以在多个子系统使用，因此该列不能跨子系统简单相加。", "",
          "### 按种类", "", "| 架构 | 种类 | 符号 | 点 |", "| --- | --- | ---: | ---: |"]
names = {"function":"函数", "object":"全局对象", "macro":"宏", "enum_constant":"枚举常量", "typedef":"类型别名", "struct":"结构体", "union":"联合体"}
for a, r in arches.items():
    for kind, n in r["by_kind"].items():
        lines.append(f"| {a} | {names.get(kind,kind)} | {n['symbols']} | {n['points']} |")
lines += ["", "### 按方向", "", "| 架构 | 方向 | 符号 | 点 |", "| --- | --- | ---: | ---: |"]
directions = {"public_to_arch":"公共→架构（含 asm-generic 默认）", "arch_to_public":"架构→公共"}
for a, r in arches.items():
    for direction, n in r["by_direction"].items():
        lines.append(f"| {a} | {directions[direction]} | {n['symbols']} | {n['points']} |")
lines += ["", f"三架构按“名称、种类、方向”取交集，共有 **{stats['common_symbols']}** 个符号组合，明细见 `common_symbols.json`。同名仅用于这个交集统计，不表示语义相同。", "", "## 两个真实例子", ""]
for direction, (s,p) in examples.items():
    u, d = p["use"], s["definition"]
    lines.append(f"- {directions[direction]}：我在 `{u['file']}:{u['line']}:{u['column']}` 记录到 `{s['name']}` 的 `{p['action']}` 引用，定义位于 `{d['file']}:{d['line']}:{d['column']}`。这个源代码点来自 {len(p['units'])} 个编译单元，合并后计 1 点。")
lines += ["", "## 链接补充与未解析部分", "", "nm 是读取目标文件和链接产物符号表的工具。我用它核对公共弱实现是否被架构强实现覆盖，并补充汇编对象的引用。它没有源代码行列，所以汇编结果单列，不加入上述 AST 边界点总数。", "",
          "| 架构 | weak 覆盖 | 汇编跨边界引用 | 汇编未解析引用 | AST 未解析引用 | 含未解析引用的 C 单元 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
for a,r in arches.items():
    o=r["object_evidence"]
    lines.append(f"| {a} | {o['weak_overrides']} | {o['asm_boundary_refs']} | {o['asm_unresolved_refs']} | {r['unresolved_refs']} | {r['units_with_unresolved_refs']} |")
lines += ["", "未解析引用是逐编译单元累计的原始计数，重复头文件会反复出现，不能与去重后的边界点直接相比。RISC-V 已保存的例子包括编译器内建的 `__has_builtin`、`__builtin_constant_p`，命令行宏 `__KERNEL__`，以及 `__compiletime_assert_*`；这些例子解释了一部分未解析项，但我没有把所有未解析项都归为内建符号。逐单元诊断见 `units_<arch>.json.gz`；未解析原因计数见 `stats.json` 的 `unresolved_by_reason`；汇编与 weak 证据见 `object_evidence_<arch>.json.gz`。未解析引用不算作零边界，也不能据此声称完全没有遗漏。", "", "## 120 条历史样本", "",
          "我以 id 对齐两份标签，排除 check=0。用已有 `functions` 中的“文件:函数”匹配 RISC-V 边界定义，或者匹配被边界函数直接调用的函数，只走一步。名称和定义文件必须都一致；没有根据文件名猜测函数，也没有自动推断改名或移动。空 functions 计为未命中，不补造符号。每条样本的证据和未命中原因保存在 `sample_hits.json`。", "",
          "| 检查 | 样本数 | 命中 | functions 为空 |", "| --- | ---: | ---: | ---: |"]
for check, r in stats["sample_hits_by_check"].items():
    lines.append(f"| {check} | {r['total']} | {r['hits']} | {r['empty_functions']} |")
lines += ["", f"合计命中 {stats['sample_hits']}/120。这是历史修复符号在当前版本构建中的出现情况，不是三类缺陷检查的查全率。未命中的 id 按 check 列在 `sample_hits.json` 的 `by_check` 中。", "", "## 局限与下一步", "",
          "我只能保证记录已编译、成功解析且 libclang 暴露的引用。未启用配置不在本次枚举范围；预处理记录没有暴露的嵌套宏数量无法取得，保留为 null；内联汇编语义和间接调用目标没有解析。汇编 nm 证据只有对象级粒度，不能替代源码位置。跨单元定义找不到或有歧义时单列未解析，不猜一个定义。", "",
          "历史函数可能删除、改名、移动，或者在当前配置里不编译；空函数字段也限制了样本命中统计。仅凭边界规模和这些命中数，还不能决定哪种定向差分模糊测试策略有效。下一步仍需研究可达性、误报和后果能否被测试观察到。", "",
          "## 文件与复现", "", "- `enumerate.py`：逐单元提取与合并；`run.sh` 直接入口，`batch.sh` 保存日志和耗时；`merge_staged.py` 将合并拆为定义阶段和每次 1024 单元的引用阶段，可从检查点续跑，已通过与原合并实现 6 个自测产物逐字节相同的核对。", "- `execution/`：本轮批次日志、计时；逐单元缓存位于 `/root/work/boundary_build/enumeration/<arch>/<输入摘要>/`，中断后重复 scan 命令即可续跑。", "- `symbols_<arch>.json`、`boundary_<arch>.jsonl.gz`：符号定义与逐点明细。", "- `direct_calls_<arch>.jsonl.gz`：直接调用边及示例位置。", "- `summarize.py`：核验明细并生成汇总、共有符号及样本命中；`report.py`：由结果生成本文。", "",
          "模型调用0；既有内核构建3（本次未重建）；新确认缺陷0；新疑点0。", ""]
(HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")
print("README written from verified stats and real boundary points")
