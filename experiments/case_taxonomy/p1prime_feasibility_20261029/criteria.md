# P1′可行性检查：判据（计数前写定，2026-10-29）

按用户“Run feasibility check”实施。只统计数量，不调用模型；研究者只看计数，不读任何对的标题、说明或diff。

## 背景

P1的40对中有28对T与S改的是同一文件，没有一对是T与S在不同架构目录；按文件位置拆分是P1之后的事后观察（M5在不同文件的12对上4/12，B1按定义为0）。本检查回答：P0b留出池里，满足P1′设定的兄弟对够不够。

## 池

`p0b_20261029/pairs_b.json`的`held_out`（6589对），去掉P1选样时按种子20261030顺序检查过的前124对（程序读过；其中前20对研究者已读）。

## 逐对判定（漏斗，逐级计数）

1. **code**：S与T都改`.c/.h`。
2. **valid_target**：T至少有一个“函数体内改动”的目标——在T的父提交中，T某个hunk的旧侧行落在某函数（`function_spans`，去预处理行后）的`{`行之后、结束行之前（纯插入取插入点）；且该函数在快照S的同一文件中存在函数体。这修正了P1中hunk上下文、声明、typedef等伪目标。
3. **not_all_seed**：有效目标不全是S自身改动的函数（同P1）。
4. **cross_file**：至少一个有效目标所在文件不在S改动的文件中；之后只保留这些跨文件目标。
5. 在cross_file之上分别计数（不互相串联）：
   - **cross_arch_dir**：某跨文件目标在`arch/X/`下，且S没有改`arch/X/`下的任何文件；
   - **fixes_tag**：T的说明含`Fixes:`行；
   - **fix_keyword**：T的标题（不分大小写）含fix、bug、leak、overflow、underflow、crash、race、deadlock、corrupt、wrong、incorrect、missing、avoid、prevent、uninitiali、null、oops、panic、hang之一；
   - **fix_like**：fixes_tag或fix_keyword；
   - **same_series**：沿用P0b字段；
   - 组合：cross_file∧fix_like、cross_file∧fix_like∧cross_arch_dir。

## 事先决策规则

- cross_file∧fix_like ≥ 40：可以在这个池上登记P1′（类缺陷修复的跨文件兄弟）。
- 否则若cross_file ≥ 40：只能把P1′定位为“同政策变更的跨文件传播”，不能称为找缺陷；向用户说明后再定。
- 否则（cross_file < 40）：P0b的同作者兄弟对挖掘撑不起跨文件回溯评估，需要换配对来源（例如不同作者、共享Fixes目标）或转向文稿重组。
- cross_arch_dir的数量只作描述，用来说明能否检验严格的跨架构设定，不改变上述规则。

## 输出

`feasibility.json`：漏斗计数与各组合计数；满足cross_file的对只保存哈希与有效目标(file, function)，留给可能的P1′选样，不打印。
