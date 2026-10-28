# 通用内核事实提取层（第二条路第一步）

2026-10-28。用户选择先补通用事实提取，使统一入口能对新源码取得事实，再评E2/E3。设计与支持域见[design.md](design.md)（实现前写定）。无模型调用、无内核启动。

## 实现

- `linux_bug_analyze/kernel_facts.py`：`collect`（WSL）对固定修订、选定架构/defconfig/配置覆盖与文件做out-of-tree构建，编译时加`-fdump-tree-cfg-lineno`，产出`bundle.json`：配置值、每个函数的反汇编与重定位行、目标文件定义符号、请求函数的预处理正文与早期CFG记录、全部SHA与命令回执；`query`只从事实包回答`defined`/`references`/`config`/`expansion_contains`/`direct_write`，回答不了就不给值。
- 适配器`kernel_source_facts`（注册进统一入口）：输入`{bundle, queries}`，回答者成为事实，未回答者列入观察记录及原因，核心据此判不足。
- `gimple_cfg_facts.analyze_cfg`与`gimple_write_effects.analyze_write_effects`新增关键字开关`real_kernel`（**默认关闭，旧结果不变**）：额外接受GCC CFG清理提示行（Merging blocks/Removing basic block）与一行签名前`__attribute__((...))`（仅cold/hot/noinline/always_inline/section），均只记为标注。修改前版本保存为`gimple_*_before_real_kernel.py`。首次属性匹配在遮罩视图上因字符串被置空而失败，改为接受括号内任意内容后通过。
- `tests/test_kernel_facts.py`3项。WSL全量450项，仍为原有2个pycparser导入错误、63跳过；第三阶段7份清单回归仍118/118与原结论一致。

## 开发回归：SPARC位宽分支改用通用事实

4个事实包（父/修复×defconfig 4096/NR_CPUS=64，3个文件均编译成功）。关系改为函数级查询：4096时`setup_arch`引用`nr_cpu_ids`与`_find_next_bit`、计数函数引用`__bitmap_weight`、`alloc_irqstack_bootmem`预处理正文含`(nr_cpu_ids)`；64时相反且计数用`__arch_hweight64`。经统一入口4/4满足，与原对象层结论一致。**粒度损失**：原判定绑定到IRQ栈循环窗口，通用事实只能说到“该函数引用了该符号”。

## 真实内核函数上的深度事实支持域

| 范围 | CFG记录 | CFG解析（real_kernel） | direct_write给值 |
| --- | --- | --- | --- |
| SPARC 6类函数×4构建 | 22/22（修复版无smp_fill_in属正确缺席） | 5类可解析；alloc_irqstack_bootmem因签名前语句不支持 | record_one_cpu与of_populate_present_mask写ncpus_probed均给“是”（与源码相符） |

开关打开前，全部真实函数CFG均为不足（清理提示行、init属性）。

## 新代码试用（试点2提交，已登记接触，不计评价）

`arch/x86/kernel/cpu/amd.c`父版，x86_64 defconfig，编译成功。试点2模型候选的10条引用中9条可映射到9个顶层函数：预处理正文9/9、CFG记录9/9、CFG可解析7/9（另2个为签名前语句/控制语句不支持）、目标文件中有独立符号5/9——另4个被内联，函数级`references`对它们不可答。这是支持域测量，未判断候选对错。

## 结论与下一步

- 稳健层（引用/配置/预处理文本）可在新代码上普遍取得；深度层（CFG/直接写）经最小开关后在真实函数上部分可用，但被内联函数与复杂语句仍是主要缺口。
- 尚缺：从模型候选（E1）自动生成查询的桥接（N1→E2）、内联函数归属到调用者、跨架构对照采集（同函数在两架构配置下的事实对比，E3所需）。
- 统一入口与适配器已变更，`eval_prep_20261028/method_freeze.json`过期，正式评价前须重新冻结。
