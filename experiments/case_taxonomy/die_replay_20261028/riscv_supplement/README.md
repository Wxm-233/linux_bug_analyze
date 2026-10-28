# die回放补充：riscv上下文（2026-10-28）

按用户“Yes, fill in riscv”补做。主回放中riscv两版均在`vdso_prepare`失败：`arch/riscv/kernel/vdso/vgettimeofday.o`的内联汇编用`csrr`，binutils≥2.38把CSR指令拆入`zicsr`扩展，须在`-march`中写出；WSL为binutils 2.42，而父版/修复版（2021年底）只传`-march=rv64imafdc`。上游在`6df2a016c0c8`（2022-01-26，riscv: fix build with binutils 2.38）追加`_zicsr_zifencei`，两版均早于该提交。

## 处理

不改历史源码、不装旧工具链：构建时加`KCFLAGS`/`KAFLAGS=-march=rv64imafdc_zicsr_zifencei`（defconfig原ISA加两扩展，效果等同上游补丁），与已声明的GCC13主机兼容选项同性质。为此`kernel_facts.collect`新增`kcflags`，附加在其自设的`KCFLAGS`（`-dD`、`-fdump-tree-cfg-lineno`）之后；只在提供时进入构建配置哈希，已有缓存键不变（复算riscv原键`96869aee1c46`一致）。先在临时目录`/tmp/riscv_zicsr_probe`手工验证修复版可构建，再经`riscv_run.py`正式构建。

## 结果

父版、修复版各构建1次，均成功；命令记录中`KCFLAGS=-dD -march=...`合并正确。沿用主回放的事实表、形式化（`die_replay_formalize`）与研究者复核，未新增模型调用。

| 事实/判定（候选0） | 父版 | 修复版 |
| --- | --- | --- |
| `topology_die_id`/`topology_die_cpumask`终态来源 | 公共回退/公共回退 | 公共回退/公共回退 |
| 导出die属性 | 是 | 否 |
| 事后契约（导出⇒两宏来自arch/） | 违反 | 满足 |
| 事后对照（导出⇒两宏已定义） | 满足 | 满足 |
| 模型形式化 | 不可表达 | 不可表达 |

候选2–4在riscv均为不适用。riscv与另外4个回退上下文一致；合并后事后契约父版1满足/5违反、修复版6满足。主回放的结论不变：事实有判别力，端到端链路未检出。riscv结果为源码与对象一致，未启动验证。

证据：`riscv_facts.json`、`riscv_results.json`、`builds/`。统计：构建2次均成功；0次Kimi调用；0内核启动；新确认缺陷0。
