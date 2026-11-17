# 复核第2版：独立检验（LoongArch未用过的22个＋MIPS 40个，只评估一次）

## 这一轮要回答什么

复核第2版在LoongArch的60个开发样本上调了两轮（`llm_review_v2_dev_20261104/`、`llm_review_v2_dev2_20261104/`）。本轮把做法冻结为开发第2轮的**单次运行**，在没用过的样本上只评估一次，看它能不能推广：
- L组：LoongArch候选池中没被抽作开发样本的22个；
- M组：第三个架构MIPS的新样本40个。

| 文件 | 说明 | SHA |
| --- | --- | --- |
| `criteria.md` | 判据，看样本之前写定 | `cd820785…` |
| `criteria_amendment1.md` | 修订1：等价性自测改为同一哈希种子下逐条一致，运行MIPS之前写 | `dd2e2f88…` |
| `criteria_amendment2.md` | 修订2：L组与开发样本的重叠单独报告，标注L组后、看MIPS候选前、调用前写 | `a8ee8b9a…` |
| `rules_mips.py`、`run_rules_mips.sh` → `selftest/`、`flags_mips/` | 规则的MIPS版（导入`rules_la.py`不改，只加常量）；自测与22个版本的标记 | 见`delivery_manifest.json` |
| `collect_test.py` → `candidates_L.json`、`candidates_M.json` | 检验候选 | 同上 |
| `evidence_test.py` → `evidence_L.json`、`evidence_M.json` | 每个候选此后改动该函数的上游提交 | 同上 |
| `make_labels3.py` → `labels3.json` | 标签与理由，生成提示词之前写定 | `05b88d09…` |
| `facts_test.py`、`build.py` → `items.json` | MIPS版程序事实与架构事实表；62个提示词 | 见`delivery_manifest.json` |
| `run_calls.py`、`check_step2.py`、`score.py` → `checks.json`、`finals.json`、`scores.json` | 调用、核对、评分（沿用开发轮，只改目录） | 同上 |
| `make_gpt_review.py` → `gpt_review/` | GPT复核材料：62条，只含规则说明、位置、理由、调用链和代码，不含程序事实和标签；附复核说明与答题表（收尾之后补做） | — |

## 做法

与开发第2轮单次运行完全相同：提示词含程序事实、架构事实表、三类判断定义和“判not_issue须有核对相符的依据”的要求；核对用`factcheck2.py`；答案有核对不符的声明或依据不被接受时追问1次。

**MIPS的移植**：
- 规则只换架构常量。陷入处理函数取`genex.S`中`BUILD_HANDLER`生成的`do_*`，加上`do_page_fault`。
- MIPS的架构事实表在看样本之前写好，共2条：
  - 进入异常时硬件置位EXL，屏蔽中断；
  - `BUILD_HANDLER`的第三个参数决定处理函数开始时中断开不开：例如`sti`表示已经打开，`cli`表示关闭，`ade`表示保持异常前的状态。
- 程序事实中，“是否由异常入口登记”这一条在MIPS上附带写出该函数的这个参数。

**自测中发现的问题（修订1）**：
- 冻结规则中，参照架构有多个同名定义时（如x86的`hibernate_32.c`和`hibernate_64.c`），选哪一个由Python每次运行的随机哈希顺序决定。所以一条R10标记（`swsusp_arch_resume`）在旧的LoongArch结果中各版本时有时无。
- 改为在两个固定种子下比较：原文件`rules_la.py`与`rules_mips.py`逐条一致，各70条。MIPS固定种子`0`运行。

## 样本与标签

| | 有修复依据的bug | 无修复依据的bug | convention | not_issue | 判断不了 |
| --- | ---: | ---: | ---: | ---: | ---: |
| L组（22） | 3 | 1 | 10 | 7 | 1 |
| M组（72个中抽40） | 0 | 2 | 3 | 34 | 1 |

- **L组与开发样本重叠（修订2）**：3个有修复依据的bug都和开发样本是同一函数、同一修复：
  - `do_ale`（v6.2）；
  - `kvm_eiointc_regs_access`；
  - `kvm_eiointc_sw_status_access`。
- **MIPS的40个都没有上游修复**：MIPS近几年基本只做维护。
- **3个无修复依据的bug**：
  - LoongArch KVM `get_gcsr_flag`：下标来自客体或用户态，检查上界后没有`array_index_nospec`；
  - MIPS `setup_arch`：早期参数`threadirqs`在`jump_label_init`之前改静态键，与LoongArch已修的问题同类，MIPS到终点版本仍未改；
  - MIPS KVM `kvm_vz_set_one_reg`：用户态下标写`maar[idx]`，没有`array_index_nospec`。

## 结果

62次调用，全部完成，约24万token。90条声明全部核对相符，42个`not_issue`的依据全部被接受，没有追问。

| | 有修复依据的bug保留 | not_issue去除 | convention不判为bug | 全部bug保留 | 问题清单（真问题/总数） |
| --- | ---: | ---: | ---: | ---: | --- |
| L组 | 3/3 | 7/7 | 10/10 | 3/4 | 3/4 |
| M组 | 0/0 | **31/34** | 3/3 | 1/2 | 1/3 |
| **合计** | 3/3 | **38/41（93%）** | **13/13** | 4/6 | 4/7 |
| 去掉与开发样本同修复的3个 | **0/0** | 38/41 | 13/13 | **1/3** | 1/4 |

问题清单的总数中，还有1个标签为“判断不了”（L组`smp_send_stop`）。

**目标是否达成**（判据第五节）：
- `not_issue`去除：38/41，达标；
- `convention`分流：13/13，达标；
- 有修复依据的bug保留：去掉重叠之后分母为0，**没有得到独立检验**。

所以按判据，不能写“推广成立”。

**判错的5个**：

| 样本 | 标签 → 判断 | 模型的理由 |
| --- | --- | --- |
| MIPS `setup_arch` | bug → not_issue | “`jump_label_init`由`start_kernel`在`setup_arch`之后统一调用” |
| LoongArch `get_gcsr_flag` | bug → convention | “读出的值只用于标志位判断，没有第二次访存，难以利用” |
| MIPS `die` | not_issue → unsure | 认为`die`可能带用户态寄存器调用 |
| MIPS `do_be` | not_issue → unsure | 认为没有可核对的依据推翻 |
| MIPS `arch_uprobe_post_xol` | not_issue → convention | 缺的是自检警告，模型判为违反约定 |

最后两个，标签和判断都不会把它放进问题清单当成真问题，影响小。

## 分析（事后，只作描述）

- **新写的MIPS架构事实起了作用**：
  - MIPS的34个`not_issue`中，大多是陷入处理函数中“关中断时可能睡眠”的标记。
  - 模型依据程序事实中写出的入口参数`sti`或`ade`，判断中断已打开或保持原状态，去掉了31个。
  - 这类标记在LoongArch第一版复核中正是误判的主要来源。
- **`setup_arch`在第二个架构上再次漏掉**：
  - 程序事实已经写明`start_kernel`中`setup_arch`在`jump_label_init`之前，MIPS目录中也有`parse_early_param`的调用。
  - 模型仍然认为“统一调用就没问题”。
  - 开发轮在LoongArch上两次漏的也是它，说明这是做法本身的系统性缺口，不是开发样本的个别现象。要判对它，需要知道“哪些早期参数会改静态键”。
- **`get_gcsr_flag`的分歧**：读出的值只用于分支判断，是否构成可利用的推测执行漏洞，确实可以讨论。标签沿用开发样本的标准：用户可控下标、检查上界后没有`array_index_nospec`，就算bug。按这个标准，它算漏判。
- **问题清单**：7个中4个是真问题。开发第2轮单次的问题清单中，真问题约占七至八成，本轮在新样本上相近。

## 结论

- **能确认推广的部分**：在没用过的LoongArch样本和新架构MIPS上，复核第2版：
  - 去掉不成立的标记达到93%，违反约定类全部分流；
  - 没有出现开发轮之外的新错误类型；
  - 换架构时，要事先写好该架构的异常入口事实，程序再把每个处理函数的入口参数作为事实给出。
- **没有得到检验的部分**：
  - 有修复依据的真问题保留。新样本中这类问题都与开发样本重叠，MIPS则没有上游修复。
  - 3个独立的无修复依据真问题只留住1个。`setup_arch`这一类问题在两个架构上都漏掉。
- **建议**：要检验真问题保留，样本需要从“有上游修复”的标记中专门收集，例如在其他架构上找后来被修的标记，而不是随机抽候选。

## 统计

模型调用62次（Claude-Sonnet-5.5，约24万token）；构建0次；新确认缺陷0；新疑点2（MIPS `setup_arch`的`threadirqs`静态键警告、MIPS KVM `kvm_vz_set_one_reg`缺`array_index_nospec`，只记录、未运行验证、未上报）。

## 事后更正（GPT复核之后）

GPT对62个标签做了盲复核，50/62一致，kappa为0.65。核实后更正4个标签，详见`gpt_review_agreement_20261104/`：
- L02、M02改为真问题：在硬中断中panic时，`smp_call_function`会触发`WARN_ON_ONCE(!in_task())`；
- M18改为真问题；
- M04改为判断不了。

按更正后的标签重算（只作描述）：
- 去掉不成立的标记：37/39（95%）；
- 违反约定的标记没被当成真问题：13/13；
- 全部真问题的保留：5/9。
