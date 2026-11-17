# 复核第2版：独立检验（判据，看样本之前写定）

## 这一轮要回答什么

复核第2版在开发样本（LoongArch 60个）上调了两轮，见`llm_review_v2_dev_20261104/`、`llm_review_v2_dev2_20261104/`。本轮把做法**冻结**，在没用过的样本上**只评估一次**，看它能不能推广：
- LoongArch没被抽中的候选；
- 第三个架构MIPS的新样本。

看过结果之后不改做法、不重跑。事后分析一律注明“事后”。

## 一、冻结的做法

与开发第2轮的**单次运行**相同，不做任何改动：
- 提示词：`llm_review_v2_dev2_20261104/build.py`的`prompt()`，即开发第1轮的提示词，加上`facts2.py`的程序事实和`bug`定义中补的一句；
- 核对：`llm_review_v2_dev_20261104/factcheck2.py`；
- 追问：开发第1轮`check_step2.py`的规则。答案中有核对不符的声明，或者`not_issue`没有被接受的依据，追问1次；
- 最终判断：追问后的答案为准。`not_issue`的依据仍不被接受的，记为`unsure`；没有拿到答案的，记为`unsure`并单独报告数目；
- 每个样本只跑1次。开发第2轮已说明两次合并的规则不宜采用。

## 二、样本

### 1. LoongArch（L组）

`llm_review_expand_20261103/`中LoongArch的候选池共82个，按种子`20261103`抽走了60个作开发样本。剩下的**22个全部使用**，不再抽样。
- 候选池用`collect_la.py`的同一段逻辑，从同一份`flags_la/`重新算出，不重跑规则；
- 去掉开发样本的键之后，个数须为22，否则停下来报告。

### 2. MIPS（M组）

**生成器**：`rules_mips.py`，导入`llm_review_expand_20261103/rules_la.py`，不修改它，只新增MIPS的一组常量：

| 位置 | LoongArch | MIPS |
| --- | --- | --- |
| 检查对象目录 | `arch/loongarch` | `arch/mips` |
| 参照架构 | arm64、x86、RISC-V | 同左 |
| 陷入处理函数（CTX的B类） | `genex.S`中`BUILD_HANDLER`生成的`do_<名字>`，加`do_page_fault`（`tlbex.S`） | `arch/mips/kernel/genex.S`中`BUILD_HANDLER`生成的`do_<名字>`（同一个正则），加`do_page_fault`（`arch/mips/mm/tlbex-fault.S`调用）；不含中断入口 |
| R7的文件范围 | `kvm/`下全部，`kernel/`下ptrace、signal、syscall、process | `arch/mips/kvm/`下全部，`arch/mips/kernel/`下ptrace、signal、syscall、process（与LoongArch相同的文件名） |
| R10不计入的架构专用词 | 原列表加`riscv`、`sbi` | 同左 |
| R10排除的自身前缀 | `loongarch` | `mips` |

**等价性自测**（运行MIPS之前）：用`rules_mips.py`对LoongArch在`v6.12`上运行，结果须与`llm_review_expand_20261103/flags_la/flags_v6.12.json`的标记逐条一致。

**快照**：`v6.1`到`v7.2`全部正式版本，共22个。

**去重与抽样**：
- 键用`llm_review_facts_20261103/candidates.py`的`key()`，同一个键只保留最早的快照；
- 多于40个时，按种子`20261104`抽40个；
- 生成器出的候选少于10个时，只作描述，不计入检验指标。

## 三、MIPS的架构事实（看样本之前写定）

**架构事实表**（对MIPS的所有CTX标记相同，放在提示词的【MIPS架构事实】中）：
1. 进入异常时，硬件置位CP0 Status寄存器的EXL位，此时中断被屏蔽。
2. 异常入口`arch/mips/kernel/genex.S`中，`BUILD_HANDLER`的第三个参数决定调用处理函数之前的中断状态：
   - `sti`、`gsexc`：打开中断；
   - `cli`、`fpe`、`msa_fpe`：关闭中断；
   - `ade`：执行`KMODE`，保持异常发生前的中断开关状态；
   - `none`：不改变，EXL仍置位，中断仍被屏蔽。

   页错误入口`arch/mips/mm/tlbex-fault.S`也执行`KMODE`。

出处：`genex.S`中的`__build_clear_*`宏，以及`arch/mips/include/asm/stackframe.h`中的`CLI`、`STI`、`KMODE`宏。

**程序事实的MIPS版本**：`facts_test.py`导入`facts2.py`，不修改它，只做三处补充：
- 架构名`mips`对应“MIPS”；
- 加入上面的架构事实表；
- “是否由异常入口代码登记”这条事实在MIPS上的判断方法与陷入处理函数相同。对`genex.S`登记的函数，括号中写出`BUILD_HANDLER`的第三个参数，例如“（arch/mips/kernel/genex.S，BUILD_HANDLER第三个参数为sti）”；同一函数在不同条件编译分支中登记了不同参数的，全部列出。`do_page_fault`写“（arch/mips/mm/tlbex-fault.S，KMODE）”，前提是该文件中有`KMODE`。

LoongArch沿用开发轮的事实与架构事实表，不改动。

**提示词的架构措辞**：MIPS样本把提示词中的“RISC-V”换成“MIPS”，R10的参照列表写“arm64、x86、RISC-V”，与LoongArch的做法相同。

## 四、标签（调用之前写定）

由第一标注人（模型Claude）逐条阅读该快照的代码，并查该快照到终点版本`df2908090cda`之间改动该函数的提交，标为四类：

| 标签 | 定义 |
| --- | --- |
| `bug`（有修复依据） | 上游后来有提交处理的正是规则所说的问题，**并且**在该快照下能选到会出错的配置和路径。这里沿用开发第2轮修订1的标准：有修复，但该快照下不会出实际错误的，标`convention` |
| `bug`（无修复依据） | 读代码认为会出实际错误，但到终点版本还没有被修 |
| `convention` | 违反写法约定，或与参照架构不一致，但该快照下不会出实际错误 |
| `not_issue` | 标记本身不成立，或只是缺少某项功能或优化 |
| `unsure` | 判断不了，不计入指标 |

- 每条写明理由。有修复依据的，写出提交号。
- 标签写入`labels3.json`，**在生成提示词之前**记录SHA。
- 看过结果之后，如果发现标签错误，只能写修订，并按同一标准重查同类的全部样本，两种标签下的结果都报告。

## 五、指标与目标（L、M两组合计，另分组报告）

| 指标 | 定义 | 目标 |
| --- | --- | --- |
| bug保留率 | 有修复依据的`bug`中，最终为`bug`或`unsure`的比例 | ≥90% |
| not_issue去除率 | `not_issue`中，最终为`not_issue`的比例 | ≥50% |
| convention分流率 | `convention`中，最终不为`bug`的比例 | ≥50% |

- 某项指标的分母少于5个时，只作描述，不判断是否达标。
- 另外报告：
  - 包括无修复依据在内的全部`bug`的保留率；
  - 问题清单（最终为`bug`或`unsure`）的大小，以及其中真问题的个数；
  - 追问次数、依据不被接受的数目。
- 三项都达标，才写“推广成立”。分母不足的指标，在结论中写明它没有得到检验。

## 六、调用

- 样本数：L组22个，M组至多40个，每个1次，另加追问。
- 模型Claude-Sonnet-5.5（配置`claude-sonnet55-20261103`），8路并行，不自动重试。
- 调用前报告调用量，须征得用户同意。
